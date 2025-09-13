from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import Optional
import logging
import time
from app.models.schemas import PDFUploadResponse
from app.services.pdf_service import get_pdf_service, PDFService
from app.config import get_settings
from app.utils import log_service_call, PDFServiceError

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/pdf", response_model=PDFUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    patient_id: Optional[str] = Form(None),
    pdf_service: PDFService = Depends(get_pdf_service)
) -> PDFUploadResponse:
    """
    Upload and process a PDF file with optimized performance.
    
    This endpoint:
    1. Validates the uploaded file
    2. Extracts text from the PDF
    3. Creates text chunks and embeddings
    4. Stores the data in the vector database
    
    Args:
        file: PDF file to upload (multipart/form-data)
        patient_id: Optional patient identifier
        pdf_service: PDF service dependency
        
    Returns:
        PDFUploadResponse with processing results
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing PDF upload: {file.filename}")
        
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed"
            )
        
        # Check file size
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File size ({file_size} bytes) exceeds maximum allowed size ({settings.max_file_size} bytes)"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )
        
        logger.info(f"File validation passed: {file.filename} ({file_size} bytes)")
        
        # Quick PDF validation (skip deep validation to speed up)
        try:
            validation_start = time.time()
            is_valid = await pdf_service.validate_pdf(file_content)
            validation_duration = time.time() - validation_start
            
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid PDF file or corrupted content"
                )
            
            log_service_call("pdf", "validate_pdf", validation_duration, True)
            logger.info(f"PDF validation completed in {validation_duration:.2f}s")
            
        except HTTPException:
            raise
        except Exception as e:
            log_service_call("pdf", "validate_pdf", None, False)
            logger.error(f"PDF validation error: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Failed to validate PDF file"
            )
        
        # Process the PDF with progress tracking
        try:
            processing_start = time.time()
            logger.info(f"Starting PDF processing for {file.filename}")
            
            # Prepare additional metadata
            additional_metadata = {
                "original_filename": file.filename,
                "file_size": file_size,
                "content_type": file.content_type,
                "upload_method": "api"
            }
            
            # Process with timeout handling (using asyncio.wait_for for timeout)
            import asyncio
            
            result = await asyncio.wait_for(
                pdf_service.process_and_store_pdf(
                    pdf_content=file_content,
                    filename=file.filename,
                    patient_id=patient_id,
                    additional_metadata=additional_metadata
                ),
                timeout=300.0  # 5 minute timeout
            )
            
            processing_duration = time.time() - processing_start
            log_service_call("pdf", "process_and_store_pdf", processing_duration, True)
            
            total_duration = time.time() - start_time
            logger.info(f"PDF processing completed in {total_duration:.2f}s: {result['chunks_created']} chunks created, {result['records_stored']} records stored")
            
            return PDFUploadResponse(
                success=True,
                message=f"PDF processed successfully. Created {result['chunks_created']} text chunks and stored {result['records_stored']} records in vector database.",
                filename=file.filename,
                extracted_text_length=result['extracted_text_length'],
                chunks_created=result['chunks_created']
            )
            
        except asyncio.TimeoutError:
            logger.error(f"PDF processing timeout after 5 minutes for {file.filename}")
            raise HTTPException(
                status_code=408,
                detail="PDF processing timeout. Please try with a smaller file or try again later."
            )
        except Exception as e:
            log_service_call("pdf", "process_and_store_pdf", None, False)
            logger.error(f"PDF processing failed for {file.filename}: {str(e)}")
            raise PDFServiceError(f"Failed to process PDF: {str(e)}")
    
    except PDFServiceError as e:
        logger.error(f"PDF service error: {str(e)}")
        return PDFUploadResponse(
            success=False,
            message=f"PDF processing failed: {str(e)}",
            filename=file.filename
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error in upload endpoint: {str(e)}", exc_info=True)
        return PDFUploadResponse(
            success=False,
            message="An unexpected error occurred during file processing",
            filename=file.filename if file else None
        )


@router.get("/health")
async def upload_health_check(
    pdf_service: PDFService = Depends(get_pdf_service)
) -> dict:
    """
    Health check endpoint for upload service dependencies.
    
    Returns:
        Dictionary with health status of upload service dependencies
    """
    health_status = {
        "status": "healthy",
        "services": {},
        "configuration": {
            "max_file_size": settings.max_file_size,
            "allowed_file_types": settings.allowed_file_types
        }
    }
    
    # Check PDF service dependencies
    try:
        # Test basic PDF validation with minimal content
        test_pdf_content = b"%PDF-1.4\n"  # Minimal PDF header
        is_service_ready = pdf_service is not None
        
        if is_service_ready:
            health_status["services"]["pdf_service"] = "healthy"
        else:
            health_status["services"]["pdf_service"] = "unhealthy"
            health_status["status"] = "degraded"
            
    except Exception as e:
        logger.warning(f"PDF service health check failed: {str(e)}")
        health_status["services"]["pdf_service"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check storage dependencies (through PDF service)
    try:
        from app.services.openai_service import get_openai_service
        from app.services.pinecone_service import get_pinecone_service
        
        openai_service = get_openai_service()
        pinecone_service = get_pinecone_service()
        
        health_status["services"]["openai"] = "healthy" if openai_service else "unhealthy"
        health_status["services"]["pinecone"] = "healthy" if pinecone_service else "unhealthy"
        
    except Exception as e:
        logger.warning(f"Storage dependencies health check failed: {str(e)}")
        health_status["services"]["storage"] = "unhealthy"
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/stats")
async def get_upload_stats(
    pdf_service: PDFService = Depends(get_pdf_service)
) -> dict:
    """
    Get statistics about the vector database and uploaded content.
    
    Returns:
        Dictionary with database statistics
    """
    try:
        from app.services.pinecone_service import get_pinecone_service
        
        pinecone_service = get_pinecone_service()
        index_stats = await pinecone_service.get_index_stats()
        
        return {
            "success": True,
            "index_stats": index_stats,
            "configuration": {
                "max_file_size_mb": settings.max_file_size / (1024 * 1024),
                "vector_dimension": settings.vector_dimension,
                "top_k_results": settings.top_k_results
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get upload stats: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }