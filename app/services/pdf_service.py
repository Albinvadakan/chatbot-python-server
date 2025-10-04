import PyPDF2
import io
import logging
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
from app.config import get_settings
from app.models.schemas import TextChunk
from app.services.openai_service import get_openai_service
from app.services.pinecone_service import get_pinecone_service

logger = logging.getLogger(__name__)
settings = get_settings()


class PDFService:
    """Service for handling PDF processing and text extraction."""
    
    def __init__(self):
        self.openai_service = get_openai_service()
        self.pinecone_service = get_pinecone_service()
        self.max_chunk_size = 1000  # Maximum characters per chunk
        self.chunk_overlap = 200    # Overlap between chunks
    
    async def extract_text_from_pdf(self, pdf_content: bytes, filename: str) -> str:
        """
        Extract text content from PDF bytes.
        
        Args:
            pdf_content: PDF file content as bytes
            filename: Original filename of the PDF
            
        Returns:
            Extracted text content
        """
        try:
            logger.info(f"Extracting text from PDF: {filename}")
            
            # Create a PDF reader from bytes
            pdf_stream = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            # Extract text from all pages
            extracted_text = ""
            page_count = len(pdf_reader.pages)
            
            for page_num in range(page_count):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                extracted_text += page_text + "\n"
            
            # Clean up the text
            cleaned_text = self._clean_text(extracted_text)
            
            logger.info(f"Extracted {len(cleaned_text)} characters from {page_count} pages")
            
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {filename}: {str(e)}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def _extract_patient_info(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract patient information from medical document text.
        
        Args:
            text: Extracted text from PDF
            
        Returns:
            Dictionary with patient_id and patient_name if found
        """
        import re
        
        patient_info = {"patient_id": None, "patient_name": None}
        
        # Clean text for better matching
        text_lines = text.replace('\n', ' ').strip()
        
        # Pattern for Patient ID (various formats)
        patient_id_patterns = [
            r'Patient\s+ID[:\s]*([a-fA-F0-9]{24,})',  # MongoDB ObjectId format
            r'Patient\s+ID[:\s]*([a-fA-F0-9-]{20,})',  # Hex with dashes
            r'Patient\s+ID[:\s]*(\d+)',  # Numeric ID
        ]
        
        # Pattern for Patient Name
        patient_name_patterns = [
            r'Patient\s+Name[:\s]*([A-Za-z\s]+?)(?:\s+Age|\s+Gender|\s+Date|\s+ID|$)',
            r'Name[:\s]*([A-Za-z\s]+?)(?:\s+Age|\s+Gender|\s+Date|\s+ID|$)',
        ]
        
        # Extract Patient ID
        for pattern in patient_id_patterns:
            match = re.search(pattern, text_lines, re.IGNORECASE)
            if match:
                patient_info["patient_id"] = match.group(1).strip()
                logger.info(f"Extracted patient ID: {patient_info['patient_id']}")
                break
        
        # Extract Patient Name
        for pattern in patient_name_patterns:
            match = re.search(pattern, text_lines, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up the name (remove extra spaces, numbers)
                name = re.sub(r'\s+', ' ', name)  # Multiple spaces to single
                name = re.sub(r'\d+', '', name).strip()  # Remove numbers
                if len(name) > 1 and not re.match(r'^[^a-zA-Z]*$', name):  # Has letters
                    patient_info["patient_name"] = name
                    logger.info(f"Extracted patient name: {patient_info['patient_name']}")
                    break
        
        return patient_info

    async def process_and_store_pdf(
        self, 
        pdf_content: bytes, 
        filename: str,
        patient_id: Optional[str] = None,
        content_type: str = "patient_private",
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process PDF, extract text, create embeddings, and store in vector database with access controls.
        
        Args:
            pdf_content: PDF file content as bytes
            filename: Original filename of the PDF
            patient_id: Optional patient identifier (required for patient_private content)
            content_type: Content classification - 'hospital_public' or 'patient_private'
            additional_metadata: Optional additional metadata
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Processing PDF: {filename}")
            
            # Extract text from PDF
            extracted_text = await self.extract_text_from_pdf(pdf_content, filename)
            
            if not extracted_text.strip():
                raise Exception("No text could be extracted from the PDF")
            
            # Handle patient information based on content type
            if content_type == "hospital_public":
                # Hospital public content - no patient-specific information
                final_patient_id = None
                final_patient_name = None
                logger.info(f"Hospital public content - accessible to all patients")
            else:
                # Patient private content - extract patient information
                extracted_patient_info = self._extract_patient_info(extracted_text)
                
                # Use extracted patient ID if not provided manually
                final_patient_id = patient_id or extracted_patient_info.get("patient_id")
                final_patient_name = extracted_patient_info.get("patient_name")
                
                logger.info(f"Patient private content - ID: {final_patient_id}, Name: {final_patient_name}")
            
            # Create text chunks
            text_chunks = self._create_text_chunks(extracted_text, filename)
            
            # Generate embeddings for chunks
            chunk_texts = [chunk.content for chunk in text_chunks]
            embeddings = await self.openai_service.generate_embeddings_batch(chunk_texts)
            
            # Prepare records for vector database
            records = []
            for chunk, embedding in zip(text_chunks, embeddings):
                metadata = {
                    "source_file": filename,
                    "chunk_index": chunk.chunk_index,
                    "upload_timestamp": datetime.utcnow().isoformat(),
                    "content_type": "pdf_extract",
                    "document_content_type": content_type  # hospital_public or patient_private
                }
                
                # Add patient information only for private content
                if content_type == "patient_private":
                    if final_patient_id:
                        metadata["patient_id"] = final_patient_id
                    if final_patient_name:
                        metadata["patient_name"] = final_patient_name
                elif content_type == "hospital_public":
                    # Mark as public hospital content
                    metadata["access_level"] = "public"
                    metadata["uploaded_by"] = "hospital_admin"
                
                if additional_metadata:
                    metadata.update(additional_metadata)
                
                records.append({
                    "record_id": chunk.chunk_id,
                    "content": chunk.content,
                    "embedding": embedding,
                    "metadata": metadata
                })
            
            # Store in vector database
            record_ids = await self.pinecone_service.upsert_patient_records_batch(records)
            
            result = {
                "success": True,
                "filename": filename,
                "extracted_text_length": len(extracted_text),
                "chunks_created": len(text_chunks),
                "records_stored": len(record_ids),
                "record_ids": record_ids,
                "content_type": content_type,
                "extracted_patient_id": final_patient_id,
                "extracted_patient_name": final_patient_name
            }
            
            logger.info(f"Successfully processed PDF {filename}: {len(text_chunks)} chunks created")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF {filename}: {str(e)}")
            raise Exception(f"Failed to process PDF: {str(e)}")
    
    def _create_text_chunks(self, text: str, source_file: str) -> List[TextChunk]:
        """
        Split text into overlapping chunks for better embedding and retrieval.
        
        Args:
            text: Text to be chunked
            source_file: Source filename
            
        Returns:
            List of TextChunk objects
        """
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Calculate end position
            end = start + self.max_chunk_size
            
            # If not at the end of text, try to break at word boundary
            if end < len(text):
                # Look for the last space before max_chunk_size
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            
            # Extract chunk content
            chunk_content = text[start:end].strip()
            
            if chunk_content:  # Only create chunk if there's content
                chunk = TextChunk(
                    chunk_id=str(uuid.uuid4()),
                    content=chunk_content,
                    chunk_index=chunk_index,
                    source_file=source_file,
                    metadata={
                        "start_position": start,
                        "end_position": end,
                        "length": len(chunk_content)
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Move start position with overlap
            start = max(start + self.max_chunk_size - self.chunk_overlap, end)
            
            # Prevent infinite loop
            if start >= len(text):
                break
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing excessive whitespace and formatting issues.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        cleaned = " ".join(text.split())
        
        # Remove common PDF artifacts
        replacements = [
            ('\x00', ''),  # Null characters
            ('\ufffd', ''),  # Replacement characters
            ('  ', ' '),  # Double spaces
        ]
        
        for old, new in replacements:
            cleaned = cleaned.replace(old, new)
        
        return cleaned.strip()
    
    async def validate_pdf(self, pdf_content: bytes) -> bool:
        """
        Validate if the provided content is a valid PDF.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            True if valid PDF, False otherwise
        """
        try:
            pdf_stream = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            # Try to access basic PDF properties
            _ = len(pdf_reader.pages)
            
            return True
            
        except Exception as e:
            logger.warning(f"PDF validation failed: {str(e)}")
            return False
    
    async def validate_knh_authorization(self, pdf_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Validate if the PDF is authorized from KNH hospital by checking for hospital identifiers.
        
        Args:
            pdf_content: PDF file content as bytes
            filename: Original filename of the PDF
            
        Returns:
            Dictionary with validation results containing 'authorized' boolean and 'reason' string
        """
        try:
            logger.info(f"Validating KNH authorization for: {filename}")
            
            # Extract text from PDF for validation
            extracted_text = await self.extract_text_from_pdf(pdf_content, filename)
            
            if not extracted_text.strip():
                return {
                    "authorized": False,
                    "reason": "Cannot validate authorization - no text could be extracted from PDF"
                }
            
            # Convert to lowercase for case-insensitive matching
            text_lower = extracted_text.lower()
            
            # Define KNH hospital validation patterns
            knh_patterns = [
                "knh",
                "hospital signature",
                "authorized by knh",
                "knh department",
                "official knh document",
                "knh medical report",
                "knh stamp",
                "hospital seal"
            ]
            
            # Additional patterns for common hospital document indicators
            hospital_patterns = [
                "hospital logo",
                "medical department",
                "doctor signature",
                "consultant signature", 
                "medical officer",
                "hospital stamp",
                "official hospital document",
                "department of",
                "medical report",
                "clinical report"
            ]
            
            found_patterns = []
            
            # Check for KNH specific patterns (high priority)
            for pattern in knh_patterns:
                if pattern in text_lower:
                    found_patterns.append(pattern)
            
            # If KNH patterns found, document is authorized
            if found_patterns:
                logger.info(f"KNH authorization validated for {filename}. Found patterns: {found_patterns}")
                return {
                    "authorized": True,
                    "reason": f"Authorized KNH document. Found: {', '.join(found_patterns)}",
                    "found_patterns": found_patterns
                }
            
            # Check for general hospital patterns (lower priority)
            hospital_found = []
            for pattern in hospital_patterns:
                if pattern in text_lower:
                    hospital_found.append(pattern)
            
            # If hospital patterns found but no KNH specific, check if it might be KNH
            if hospital_found:
                # Additional check for any form of "kenyatta" or hospital identifiers
                if any(keyword in text_lower for keyword in ["kenyatta", "national hospital", "hospital"]):
                    logger.info(f"Potential KNH document validation for {filename}. Found patterns: {hospital_found}")
                    return {
                        "authorized": True,
                        "reason": f"Authorized hospital document. Found: {', '.join(hospital_found)}",
                        "found_patterns": hospital_found
                    }
            
            # No authorization patterns found
            logger.warning(f"KNH authorization failed for {filename}. No valid hospital identifiers found.")
            return {
                "authorized": False,
                "reason": "Cannot upload - document does not contain KNH hospital identifiers, signatures, or authorized labels"
            }
            
        except Exception as e:
            logger.error(f"Error during KNH authorization validation for {filename}: {str(e)}")
            return {
                "authorized": False,
                "reason": f"Authorization validation failed due to processing error: {str(e)}"
            }
    
    async def get_pdf_info(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Extract metadata information from PDF.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary with PDF metadata
        """
        try:
            pdf_stream = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            info = {
                "page_count": len(pdf_reader.pages),
                "file_size": len(pdf_content)
            }
            
            # Extract PDF metadata if available
            if pdf_reader.metadata:
                metadata = pdf_reader.metadata
                info.update({
                    "title": metadata.get("/Title", ""),
                    "author": metadata.get("/Author", ""),
                    "subject": metadata.get("/Subject", ""),
                    "creator": metadata.get("/Creator", ""),
                    "producer": metadata.get("/Producer", ""),
                    "creation_date": str(metadata.get("/CreationDate", "")),
                    "modification_date": str(metadata.get("/ModDate", ""))
                })
            
            return info
            
        except Exception as e:
            logger.error(f"Error extracting PDF info: {str(e)}")
            return {"error": str(e)}


# Global service instance
pdf_service = PDFService()


def get_pdf_service() -> PDFService:
    """Get PDF service instance."""
    return pdf_service