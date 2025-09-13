from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging
import time
from app.models.schemas import ChatRequest, ChatResponse, PatientRecord
from app.services.openai_service import get_openai_service, OpenAIService
from app.services.pinecone_service import get_pinecone_service, PineconeService
from app.utils import log_service_call, OpenAIServiceError, PineconeServiceError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ai-response", response_model=ChatResponse)
async def chat_ai_response(
    request: ChatRequest,
    openai_service: OpenAIService = Depends(get_openai_service),
    pinecone_service: PineconeService = Depends(get_pinecone_service)
) -> ChatResponse:
    """
    Generate AI response using OpenAI GPT with patient context from vector database.
    
    This endpoint:
    1. Takes a user query
    2. Generates an embedding for the query
    3. Searches for relevant patient records in Pinecone cloud
    4. Uses the context to generate an AI response
    
    Args:
        request: ChatRequest with user query
        openai_service: OpenAI service dependency
        pinecone_service: Pinecone service dependency
        
    Returns:
        ChatResponse with AI-generated response and relevant patient context
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing chat request: {request.query[:100]}...")
        
        # Step 1: Generate embedding for the query
        try:
            embedding_start = time.time()
            embedding_response = await openai_service.generate_embedding(request.query)
            embedding_duration = time.time() - embedding_start
            
            log_service_call("openai", "generate_embedding", embedding_duration, True)
            
        except Exception as e:
            log_service_call("openai", "generate_embedding", None, False)
            raise OpenAIServiceError(f"Failed to generate query embedding: {str(e)}")
        
        # Step 2: Search for relevant patient records
        patient_context = []
        try:
            search_start = time.time()
            search_result = await pinecone_service.search_patient_history(
                query=request.query,
                query_embedding=embedding_response.embedding
            )
            search_duration = time.time() - search_start
            
            patient_context = search_result.records
            log_service_call("pinecone", "search_patient_history", search_duration, True)
            
            logger.info(f"Found {len(patient_context)} relevant patient records")
            
        except Exception as e:
            log_service_call("pinecone", "search_patient_history", None, False)
            logger.warning(f"Failed to search patient history: {str(e)}")
            # Continue without patient context rather than failing completely
        
        # Step 3: Generate AI response with context
        try:
            response_start = time.time()
            ai_response = await openai_service.generate_chat_response(
                query=request.query,
                patient_context=patient_context
            )
            response_duration = time.time() - response_start
            
            log_service_call("openai", "generate_chat_response", response_duration, True)
            
        except Exception as e:
            log_service_call("openai", "generate_chat_response", None, False)
            raise OpenAIServiceError(f"Failed to generate AI response: {str(e)}")
        
        # Prepare patient context for response (limit to preserve response size)
        context_for_response = []
        for record in patient_context[:3]:  # Limit to top 3 records
            context_for_response.append({
                "record_id": record.record_id,
                "content": record.content[:200] + "..." if len(record.content) > 200 else record.content,
                "score": record.score,
                "metadata": {
                    "patient_id": record.patient_id,
                    "source": record.metadata.get("source_file", "unknown")
                }
            })
        
        total_duration = time.time() - start_time
        logger.info(f"Chat request completed in {total_duration:.2f}s")
        
        return ChatResponse(
            response=ai_response,
            patient_context=context_for_response if context_for_response else None
        )
        
    except OpenAIServiceError as e:
        logger.error(f"OpenAI service error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"AI service temporarily unavailable: {str(e)}"
        )
    
    except PineconeServiceError as e:
        logger.error(f"Pinecone service error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Search service temporarily unavailable: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your request"
        )


@router.get("/health")
async def chat_health_check(
    openai_service: OpenAIService = Depends(get_openai_service),
    pinecone_service: PineconeService = Depends(get_pinecone_service)
) -> Dict[str, Any]:
    """
    Health check endpoint for chat service dependencies.
    
    Returns:
        Dictionary with health status of chat service dependencies
    """
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Check OpenAI service
    try:
        # Simple test with minimal usage
        await openai_service.generate_embedding("test")
        health_status["services"]["openai"] = "healthy"
    except Exception as e:
        logger.warning(f"OpenAI health check failed: {str(e)}")
        health_status["services"]["openai"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check vector storage service
    try:
        await vector_service.get_index_stats()
        health_status["services"]["vector_storage"] = "healthy"
    except Exception as e:
        logger.warning(f"Vector storage health check failed: {str(e)}")
        health_status["services"]["vector_storage"] = "unhealthy"
        health_status["status"] = "degraded"
    
    return health_status