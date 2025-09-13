from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from contextlib import asynccontextmanager

from app.config import get_settings
from app.utils import (
    setup_logging,
    global_exception_handler,
    validation_exception_handler,
    log_request_info
)
from app.routers import chat, upload
from app.models.schemas import HealthResponse, ErrorResponse

# Initialize settings and logging
settings = get_settings()
setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Initialize services (they will be initialized when first accessed)
    try:
        from app.services.openai_service import get_openai_service
        from app.services.pinecone_service import get_pinecone_service
        from app.services.pdf_service import get_pdf_service
        
        # Test service connections
        openai_service = get_openai_service()
        pinecone_service = get_pinecone_service()
        pdf_service = get_pdf_service()
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        # Continue startup even if services fail - they will be retried on first use
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Application shutdown initiated")
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    A FastAPI-based chatbot server with PDF processing capabilities and vector database integration.
    
    ## Features
    
    * **Chat API**: AI-powered responses using OpenAI GPT with patient context
    * **PDF Upload**: Extract text from PDFs and store in vector database
    * **Vector Search**: Query patient history using semantic search
    * **LangChain Integration**: Advanced language model operations
    
    ## Authentication
    
    Currently, this API does not require authentication. In production, implement proper authentication and authorization.
    
    ## Rate Limiting
    
    No rate limiting is currently implemented. Consider adding rate limiting for production use.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(ValueError, validation_exception_handler)


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing information."""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    process_time = time.time() - start_time
    
    # Log request info
    log_request_info(request, process_time)
    
    # Add response time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Include routers
app.include_router(
    chat.router,
    prefix="/api/v1/chat",
    tags=["Chat"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"}
    }
)

app.include_router(
    upload.router,
    prefix="/api/v1/upload",
    tags=["Upload"],
    responses={
        400: {"description": "Bad request"},
        413: {"description": "File too large"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)


# Root endpoint
@app.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    """
    Root endpoint with basic application information.
    
    Returns:
        HealthResponse with application status and version
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        services={
            "chat": "available",
            "upload": "available"
        }
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check endpoint.
    
    Returns:
        HealthResponse with detailed service status
    """
    service_status = {}
    overall_status = "healthy"
    
    try:
        # Check OpenAI service
        from app.services.openai_service import get_openai_service
        openai_service = get_openai_service()
        service_status["openai"] = "healthy" if openai_service else "unhealthy"
        
    except Exception as e:
        logger.warning(f"OpenAI service health check failed: {str(e)}")
        service_status["openai"] = "unhealthy"
        overall_status = "degraded"
    
    try:
        # Check Pinecone service
        from app.services.pinecone_service import get_pinecone_service
        pinecone_service = get_pinecone_service()
        # Simple check - if service exists and has an index, it's healthy
        service_status["pinecone"] = "healthy" if pinecone_service and hasattr(pinecone_service, '_index') else "unhealthy"
        
    except Exception as e:
        logger.warning(f"Pinecone service health check failed: {str(e)}")
        service_status["pinecone"] = "unhealthy"
        overall_status = "degraded"
    
    try:
        # Check PDF service
        from app.services.pdf_service import get_pdf_service
        pdf_service = get_pdf_service()
        service_status["pdf"] = "healthy" if pdf_service else "unhealthy"
        
    except Exception as e:
        logger.warning(f"PDF service health check failed: {str(e)}")
        service_status["pdf"] = "unhealthy"
        overall_status = "degraded"
    
    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        services=service_status
    )


# Configuration endpoint
@app.get("/config")
async def get_config() -> dict:
    """
    Get public configuration information.
    
    Returns:
        Dictionary with non-sensitive configuration details
    """
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "debug": settings.debug,
        "max_file_size_mb": settings.max_file_size / (1024 * 1024),
        "allowed_file_types": settings.allowed_file_types,
        "max_tokens": settings.max_tokens,
        "temperature": settings.temperature,
        "top_k_results": settings.top_k_results,
        "vector_dimension": settings.vector_dimension
    }


# Custom error pages
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors with custom response."""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error="NOT_FOUND",
            message=f"The requested endpoint {request.url.path} was not found"
        ).model_dump()
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    """Handle 405 errors with custom response."""
    return JSONResponse(
        status_code=405,
        content=ErrorResponse(
            error="METHOD_NOT_ALLOWED",
            message=f"Method {request.method} is not allowed for {request.url.path}"
        ).model_dump()
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )