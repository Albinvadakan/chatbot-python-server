import logging
import sys
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pythonjsonlogger import jsonlogger
from app.config import get_settings
from app.models.schemas import ErrorResponse

settings = get_settings()


def setup_logging():
    """Configure application logging."""
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Create JSON formatter
    json_formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)
    
    # Set levels for specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("pinecone").setLevel(logging.INFO)
    
    logger.info("Logging configured successfully")


class APIException(HTTPException):
    """Custom API exception with enhanced error details."""
    
    def __init__(
        self,
        status_code: int,
        error_type: str,
        message: str,
        details: dict = None
    ):
        self.error_type = error_type
        self.details = details or {}
        super().__init__(status_code=status_code, detail=message)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled exceptions.
    
    Args:
        request: FastAPI request object
        exc: Exception that occurred
        
    Returns:
        JSON error response
    """
    logger = logging.getLogger(__name__)
    
    if isinstance(exc, APIException):
        # Handle custom API exceptions
        error_response = ErrorResponse(
            error=exc.error_type,
            message=exc.detail,
            details=exc.details
        )
        
        logger.error(
            f"API Exception: {exc.error_type}",
            extra={
                "status_code": exc.status_code,
                "message": exc.detail,
                "details": exc.details,
                "path": str(request.url)
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump()
        )
    
    elif isinstance(exc, HTTPException):
        # Handle FastAPI HTTP exceptions
        error_response = ErrorResponse(
            error="HTTP_ERROR",
            message=exc.detail,
            details={"status_code": exc.status_code}
        )
        
        logger.error(
            f"HTTP Exception: {exc.status_code}",
            extra={
                "message": exc.detail,
                "path": str(request.url)
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump()
        )
    
    else:
        # Handle unexpected exceptions
        error_response = ErrorResponse(
            error="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            details={"exception_type": type(exc).__name__}
        )
        
        logger.error(
            f"Unexpected Exception: {type(exc).__name__}",
            extra={
                "message": str(exc),
                "path": str(request.url)
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump()
        )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle validation exceptions from Pydantic models.
    
    Args:
        request: FastAPI request object
        exc: Validation exception
        
    Returns:
        JSON error response
    """
    logger = logging.getLogger(__name__)
    
    error_response = ErrorResponse(
        error="VALIDATION_ERROR",
        message="Request validation failed",
        details={"validation_errors": str(exc)}
    )
    
    logger.warning(
        "Validation error",
        extra={
            "message": str(exc),
            "path": str(request.url)
        }
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump()
    )


class ServiceError(Exception):
    """Base exception for service errors."""
    
    def __init__(self, message: str, service: str, details: dict = None):
        self.message = message
        self.service = service
        self.details = details or {}
        super().__init__(message)


class OpenAIServiceError(ServiceError):
    """Exception for OpenAI service errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "openai", details)


class PineconeServiceError(ServiceError):
    """Exception for Pinecone service errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "pinecone", details)


class PDFServiceError(ServiceError):
    """Exception for PDF service errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "pdf", details)


def log_request_info(request: Request, response_time: float = None):
    """
    Log request information.
    
    Args:
        request: FastAPI request object
        response_time: Response time in seconds
    """
    logger = logging.getLogger("app.requests")
    
    log_data = {
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if response_time:
        log_data["response_time"] = response_time
    
    logger.info("Request processed", extra=log_data)


def log_service_call(service: str, operation: str, duration: float = None, success: bool = True):
    """
    Log service call information.
    
    Args:
        service: Name of the service
        operation: Operation performed
        duration: Operation duration in seconds
        success: Whether the operation was successful
    """
    logger = logging.getLogger(f"app.services.{service}")
    
    log_data = {
        "operation": operation,
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if duration:
        log_data["duration"] = duration
    
    level = logging.INFO if success else logging.ERROR
    message = f"Service operation {'completed' if success else 'failed'}: {operation}"
    
    logger.log(level, message, extra=log_data)