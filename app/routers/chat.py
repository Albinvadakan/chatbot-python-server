from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging
import time
from app.models.schemas import ChatRequest, ChatResponse, PatientRecord
from app.services.openai_service import get_openai_service, OpenAIService
from app.services.pinecone_service import get_pinecone_service, PineconeService
from app.utils import log_service_call, OpenAIServiceError, PineconeServiceError, is_patient_specific_query

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
        
        # Step 1: Classify query type and determine filtering requirements
        is_patient_query = is_patient_specific_query(request.query)
        patient_id_for_filtering = None
        
        if is_patient_query and request.patientId:
            patient_id_for_filtering = request.patientId
            logger.info(f"Patient-specific query detected for patient: {request.patientId}")
        elif is_patient_query:
            logger.warning("Patient-specific query detected but no patient ID provided")
        else:
            logger.info("General query detected - no patient filtering required")
        
        # Step 2: Generate embedding for the query
        try:
            embedding_start = time.time()
            embedding_response = await openai_service.generate_embedding(request.query)
            embedding_duration = time.time() - embedding_start
            
            log_service_call("openai", "generate_embedding", embedding_duration, True)
            
        except Exception as e:
            log_service_call("openai", "generate_embedding", None, False)
            raise OpenAIServiceError(f"Failed to generate query embedding: {str(e)}")
        
        # Step 3: Search for relevant records with mixed content filtering
        patient_context = []
        try:
            search_start = time.time()
            
            if is_patient_query and patient_id_for_filtering:
                # Patient-specific query: include patient's private content + hospital public content
                search_result = await pinecone_service.search_patient_history(
                    query=request.query,
                    query_embedding=embedding_response.embedding,
                    patient_id=patient_id_for_filtering,
                    include_public_content=True
                )
                logger.info(f"Patient-specific search for {patient_id_for_filtering} (includes public hospital content)")
            elif is_patient_query:
                # Patient-specific query without patient ID: only hospital public content
                search_result = await pinecone_service.search_patient_history(
                    query=request.query,
                    query_embedding=embedding_response.embedding,
                    patient_id=None,
                    include_public_content=True
                )
                logger.info(f"Patient query without ID: only public hospital content")
            else:
                # General query: hospital public content + patient private (if patient ID provided)
                search_result = await pinecone_service.search_patient_history(
                    query=request.query,
                    query_embedding=embedding_response.embedding,
                    patient_id=patient_id_for_filtering,
                    include_public_content=True
                )
                logger.info(f"General query: public content + patient content for {patient_id_for_filtering or 'no patient'}")
            
            search_duration = time.time() - search_start
            patient_context = search_result.records
            log_service_call("pinecone", "search_patient_history", search_duration, True)
            
            logger.info(f"Found {len(patient_context)} total records")
            
            # Log content type breakdown for debugging
            public_count = sum(1 for r in patient_context if r.metadata.get("document_content_type") == "hospital_public")
            private_count = len(patient_context) - public_count
            logger.info(f"Content breakdown: {public_count} public, {private_count} private records")
            
        except Exception as e:
            log_service_call("pinecone", "search_patient_history", None, False)
            logger.warning(f"Failed to search patient history: {str(e)}")
            # Continue without patient context rather than failing completely
        
        # Step 4: Generate AI response with appropriate context and privacy controls
        try:
            response_start = time.time()
            ai_response = await openai_service.generate_chat_response(
                query=request.query,
                patient_context=patient_context,
                is_patient_specific=is_patient_query,
                patient_name=request.patientName
            )
            response_duration = time.time() - response_start
            
            log_service_call("openai", "generate_chat_response", response_duration, True)
            
        except Exception as e:
            log_service_call("openai", "generate_chat_response", None, False)
            raise OpenAIServiceError(f"Failed to generate AI response: {str(e)}")
        
        # Prepare context for response (with content type classification)
        context_for_response = []
        for record in patient_context[:3]:  # Limit to top 3 records
            record_metadata = record.metadata or {}
            content_type = record_metadata.get("document_content_type", "unknown")
            
            # Determine what to show based on content type
            if content_type == "hospital_public":
                # Hospital public content - show as public
                metadata_for_response = {
                    "content_type": "hospital_public",
                    "source": record_metadata.get("source_file", "unknown"),
                    "access_level": "public",
                    "query_classification": "patient_specific" if is_patient_query else "general"
                }
            elif content_type == "patient_private":
                # Patient private content - only show if it's the correct patient
                if patient_id_for_filtering and record.patient_id == patient_id_for_filtering:
                    metadata_for_response = {
                        "content_type": "patient_private",
                        "patient_id": record.patient_id,
                        "source": record_metadata.get("source_file", "unknown"),
                        "access_level": "private",
                        "query_classification": "patient_specific" if is_patient_query else "general"
                    }
                else:
                    # Skip this record - wrong patient or no patient ID
                    logger.warning(f"Filtering out private record {record.record_id} - patient mismatch")
                    continue
            else:
                # Unknown content type - treat as private and filter carefully
                if patient_id_for_filtering and record.patient_id == patient_id_for_filtering:
                    metadata_for_response = {
                        "content_type": "unknown",
                        "patient_id": record.patient_id,
                        "source": record_metadata.get("source_file", "unknown"),
                        "access_level": "private",
                        "query_classification": "patient_specific" if is_patient_query else "general"
                    }
                else:
                    continue
            
            context_for_response.append({
                "record_id": record.record_id,
                "content": record.content[:200] + "..." if len(record.content) > 200 else record.content,
                "score": record.score,
                "metadata": metadata_for_response
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
    
    # Check Pinecone service
    try:
        # Simple index status check
        if hasattr(pinecone_service, 'index') and pinecone_service.index:
            health_status["services"]["pinecone"] = "healthy"
        else:
            health_status["services"]["pinecone"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.warning(f"Pinecone health check failed: {str(e)}")
        health_status["services"]["pinecone"] = "unhealthy"
        health_status["status"] = "degraded"
    
    return health_status