from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for chat API."""
    query: str = Field(..., description="User query for the AI chatbot", min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """Response model for chat API."""
    response: str = Field(..., description="AI-generated response")
    patient_context: Optional[List[Dict[str, Any]]] = Field(default=None, description="Relevant patient records")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class PDFUploadResponse(BaseModel):
    """Response model for PDF upload."""
    success: bool = Field(..., description="Upload success status")
    message: str = Field(..., description="Upload status message")
    filename: Optional[str] = Field(default=None, description="Uploaded filename")
    extracted_text_length: Optional[int] = Field(default=None, description="Length of extracted text")
    chunks_created: Optional[int] = Field(default=None, description="Number of text chunks created")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")


class PatientRecord(BaseModel):
    """Model for patient record data."""
    record_id: str = Field(..., description="Unique record identifier")
    patient_id: Optional[str] = Field(default=None, description="Patient identifier")
    content: str = Field(..., description="Record content/text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    score: Optional[float] = Field(default=None, description="Similarity score from vector search")
    timestamp: Optional[datetime] = Field(default=None, description="Record timestamp")


class SearchResult(BaseModel):
    """Model for search results from vector database."""
    records: List[PatientRecord] = Field(..., description="List of matching patient records")
    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total number of results found")
    search_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Search timestamp")


class EmbeddingRequest(BaseModel):
    """Request model for text embedding."""
    text: str = Field(..., description="Text to be embedded", min_length=1)
    model: Optional[str] = Field(default="text-embedding-ada-002", description="Embedding model to use")


class EmbeddingResponse(BaseModel):
    """Response model for text embedding."""
    embedding: List[float] = Field(..., description="Text embedding vector")
    model: str = Field(..., description="Model used for embedding")
    dimensions: int = Field(..., description="Embedding dimensions")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Detailed error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(default="healthy", description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    version: str = Field(..., description="Application version")
    services: Dict[str, str] = Field(default_factory=dict, description="External service status")


class TextChunk(BaseModel):
    """Model for text chunks from PDF processing."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk content")
    chunk_index: int = Field(..., description="Chunk index in the document")
    source_file: str = Field(..., description="Source PDF filename")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")