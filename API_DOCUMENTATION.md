# Chatbot Python Server API Documentation

## Overview
A FastAPI-based chatbot server with PDF processing capabilities, OpenAI integration, and Pinecone vector database for semantic search. The server provides intelligent responses based on uploaded patient documents.

## Base Information
- **Server URL**: `http://localhost:8000`
- **API Version**: v1
- **Framework**: FastAPI
- **Python Version**: 3.13+
- **Interactive Docs**: `http://localhost:8000/docs`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## Authentication
Currently, the API does not require authentication. All endpoints are publicly accessible.

## API Endpoints

### 1. Health Check
**GET** `/health`

Returns the health status of the server and all connected services.

**Response Example:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-13T11:18:01.123Z",
  "services": {
    "openai": "healthy",
    "pinecone": "healthy",
    "pdf_processor": "healthy"
  },
  "version": "1.0.0"
}
```

**Response Codes:**
- `200 OK`: All services healthy
- `503 Service Unavailable`: One or more services degraded

---

### 2. Chat AI Response
**POST** `/api/v1/chat/ai-response`

Generate AI-powered responses using OpenAI GPT with context from uploaded patient documents.

**Request Body:**
```json
{
  "query": "What are the patient's symptoms?"
}
```

**Request Schema:**
- `query` (string, required): User question or query

**Process Flow:**
1. Generate embedding for the user query
2. Search Pinecone vector database for relevant patient records
3. Use retrieved context to generate AI response
4. Return contextual response

**Response Example:**
```json
{
  "response": "Based on the patient records, the symptoms include fever, cough, and fatigue. The patient reported onset 3 days ago with mild to moderate severity.",
  "context_used": true,
  "records_found": 3,
  "processing_time": 2.45
}
```

**Response Schema:**
- `response` (string): AI-generated response
- `context_used` (boolean): Whether patient context was used
- `records_found` (integer): Number of relevant records found
- `processing_time` (float): Processing time in seconds

**Response Codes:**
- `200 OK`: Successful response generation
- `400 Bad Request`: Invalid request format
- `500 Internal Server Error`: AI service error

---

### 3. PDF Upload and Processing
**POST** `/api/v1/upload/pdf`

Upload and process PDF files to extract text, create embeddings, and store in vector database.

**Request Type:** `multipart/form-data`

**Parameters:**
- `file` (file, required): PDF file to upload
- `patient_id` (string, optional): Patient identifier for metadata

**File Validation:**
- **Max Size**: 10MB
- **Allowed Types**: PDF only
- **Content**: Must contain extractable text

**Processing Pipeline:**
1. File validation (type, size, content)
2. PDF text extraction using PyPDF2
3. Text chunking (1000 chars max, 200 char overlap)
4. OpenAI embedding generation (batch processed)
5. Vector storage in Pinecone cloud database

**Response Example:**
```json
{
  "success": true,
  "message": "PDF processed successfully. Created 15 text chunks and stored 15 records in vector database.",
  "filename": "patient_report.pdf",
  "extracted_text_length": 12450,
  "chunks_created": 15
}
```

**Response Schema:**
- `success` (boolean): Processing success status
- `message` (string): Detailed processing message
- `filename` (string): Original filename
- `extracted_text_length` (integer): Total characters extracted
- `chunks_created` (integer): Number of text chunks created

**Error Response Example:**
```json
{
  "success": false,
  "message": "PDF processing failed: Invalid PDF file or corrupted content",
  "filename": "corrupted_file.pdf"
}
```

**Response Codes:**
- `200 OK`: Successful processing
- `400 Bad Request`: Invalid file or validation error
- `408 Request Timeout`: Processing timeout (5 minutes)
- `413 Payload Too Large`: File exceeds size limit
- `500 Internal Server Error`: Processing error

---

## Data Models

### ChatRequest
```json
{
  "query": "string (required)"
}
```

### ChatResponse
```json
{
  "response": "string",
  "context_used": "boolean",
  "records_found": "integer",
  "processing_time": "float"
}
```

### PDFUploadResponse
```json
{
  "success": "boolean",
  "message": "string",
  "filename": "string",
  "extracted_text_length": "integer",
  "chunks_created": "integer"
}
```

### HealthResponse
```json
{
  "status": "string",
  "timestamp": "string",
  "services": {
    "openai": "string",
    "pinecone": "string",
    "pdf_processor": "string"
  },
  "version": "string"
}
```

---

## Configuration

### Environment Variables
```env
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
MAX_TOKENS=1000
TEMPERATURE=0.7

# Pinecone Configuration
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_NAME=knh-index

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# File Processing
MAX_FILE_SIZE=10485760  # 10MB
VECTOR_DIMENSION=1536
TOP_K_RESULTS=3
```

### Service Dependencies
- **OpenAI API**: GPT models for chat completion and embeddings
- **Pinecone**: Vector database for semantic search
- **PyPDF2**: PDF text extraction
- **FastAPI**: Web framework
- **Uvicorn**: ASGI server

---

## Usage Examples

### 1. Upload a PDF Document
```bash
curl -X POST "http://localhost:8000/api/v1/upload/pdf" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@patient_report.pdf" \
     -F "patient_id=PATIENT_001"
```

### 2. Query Patient Information
```bash
curl -X POST "http://localhost:8000/api/v1/chat/ai-response" \
     -H "Content-Type: application/json" \
     -d '{"query": "What medications is the patient currently taking?"}'
```

### 3. Check Server Health
```bash
curl -X GET "http://localhost:8000/health"
```

### 4. View API Documentation
```bash
# Open in browser
http://localhost:8000/docs
```

---

## Performance Optimizations

### Upload Service
- **Batch Processing**: Up to 100 vectors per Pinecone batch
- **Chunked Embeddings**: Process 2000 texts per OpenAI batch
- **Timeout Handling**: 5-minute processing timeout
- **Progress Logging**: Real-time processing updates

### Vector Database
- **Auto-Scaling**: Pinecone serverless with auto-scaling
- **Efficient Search**: Cosine similarity with top-k results
- **Metadata Storage**: Rich metadata for enhanced retrieval

### AI Processing
- **Context Injection**: Relevant patient records included in prompts
- **Model Optimization**: GPT-3.5-turbo for balanced speed/quality
- **Embedding Caching**: Efficient batch embedding generation

---

## Error Handling

### Common Error Codes
- `400 Bad Request`: Invalid input data or file format
- `408 Request Timeout`: Processing exceeded time limit
- `413 Payload Too Large`: File size exceeds maximum
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Service failure
- `503 Service Unavailable`: External service unavailable

### Error Response Format
```json
{
  "detail": "Error description",
  "status_code": 400,
  "timestamp": "2025-09-13T11:18:01.123Z"
}
```

---

## Security Considerations

### Current Implementation
- No authentication required
- CORS enabled for all origins
- File validation for uploads
- Input sanitization for text processing

### Recommended Enhancements
- API key authentication
- Rate limiting
- Input validation middleware
- Audit logging
- HTTPS enforcement

---

## Monitoring and Logging

### Log Levels
- `INFO`: General operation logs
- `WARNING`: Non-critical issues
- `ERROR`: Service failures
- `DEBUG`: Detailed debugging info

### Metrics Tracked
- Request processing time
- File upload success/failure rates
- Vector database operations
- OpenAI API usage
- Service health status

---

## Development

### Local Setup
```bash
# 1. Clone repository
git clone <repository-url>

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Start server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run tests
pytest

# Test coverage
pytest --cov=app

# Integration tests
pytest tests/integration/
```

---

## Support

### Documentation
- Interactive API docs: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`
- OpenAPI schema: `http://localhost:8000/openapi.json`

### Troubleshooting
1. Check server logs for detailed error messages
2. Verify environment variables are correctly set
3. Ensure external services (OpenAI, Pinecone) are accessible
4. Check file permissions and disk space for uploads

---

## Version History

### v1.0.0 (Current)
- Initial release
- PDF upload and processing
- OpenAI chat integration
- Pinecone vector search
- Health monitoring
- Performance optimizations

---

*Last Updated: September 13, 2025*
*Server Version: 1.0.0*