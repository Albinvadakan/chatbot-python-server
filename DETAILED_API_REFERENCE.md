# Complete API Details - Chat AI Response & PDF Upload

## 1. Chat AI Response API

### **POST** `/api/v1/chat/ai-response`

Generates intelligent AI responses using OpenAI GPT with contextual information from uploaded patient documents.

---

#### **Request Details**

**Headers:**
```
Content-Type: application/json
Accept: application/json
```

**Request Body Schema:**
```json
{
  "query": "string"
}
```

**Field Specifications:**
- `query` (string, required):
  - **Description**: User question or query for the AI chatbot
  - **Constraints**: 
    - Minimum length: 1 character
    - Maximum length: 2000 characters
  - **Examples**: 
    - "What are the patient's symptoms?"
    - "What medications is the patient currently taking?"
    - "Summarize the patient's medical history"

---

#### **Processing Pipeline**

The endpoint follows a 3-step process:

1. **Query Embedding Generation**
   - Converts user query to vector representation using OpenAI `text-embedding-ada-002`
   - Vector dimension: 1536
   - Processing time: ~0.1-0.5 seconds

2. **Vector Database Search**
   - Searches Pinecone cloud database for semantically similar patient records
   - Uses cosine similarity matching
   - Returns top 3 most relevant records by default
   - Processing time: ~0.2-1.0 seconds

3. **Contextual AI Response Generation**
   - Injects relevant patient context into GPT prompt
   - Uses GPT-3.5-turbo model for response generation
   - Temperature: 0.7 (balanced creativity/consistency)
   - Max tokens: 1000
   - Processing time: ~1-3 seconds

---

#### **Response Details**

**Success Response (200 OK):**
```json
{
  "response": "Based on the patient records, the patient is experiencing fever (101.5°F), persistent cough, and fatigue for the past 3 days. The symptoms began gradually and have been progressively worsening.",
  "patient_context": [
    {
      "record_id": "chunk_abc123",
      "content": "Patient reports fever, cough, and fatigue beginning 3 days ago. Temperature recorded at 101.5°F. Cough is dry and persistent...",
      "score": 0.895,
      "metadata": {
        "patient_id": "PATIENT_001",
        "source": "medical_report_20250913.pdf"
      }
    },
    {
      "record_id": "chunk_def456",
      "content": "Previous visit notes indicate patient has no known allergies. Current medications include...",
      "score": 0.782,
      "metadata": {
        "patient_id": "PATIENT_001",
        "source": "consultation_notes.pdf"
      }
    }
  ],
  "timestamp": "2025-09-13T11:30:45.123Z"
}
```

**Response Schema:**
- `response` (string): AI-generated contextual response
- `patient_context` (array, optional): Relevant patient records used for context
  - `record_id` (string): Unique identifier for the record chunk
  - `content` (string): Text content (truncated to 200 chars for response)
  - `score` (float): Similarity score (0-1, higher = more relevant)
  - `metadata` (object): Additional record information
    - `patient_id` (string): Patient identifier
    - `source` (string): Source filename
- `timestamp` (string): ISO 8601 response timestamp

---

#### **Error Responses**

**400 Bad Request:**
```json
{
  "detail": "Query length exceeds maximum allowed (2000 characters)"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**503 Service Unavailable:**
```json
{
  "detail": "AI service temporarily unavailable: OpenAI API rate limit exceeded"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "An unexpected error occurred while processing your request"
}
```

---

#### **Performance Characteristics**

- **Average Response Time**: 2-5 seconds
- **Timeout**: 30 seconds (configurable)
- **Rate Limiting**: Dependent on OpenAI API limits
- **Concurrent Requests**: Supports async processing
- **Memory Usage**: ~50MB per request (embeddings + context)

---

#### **Usage Examples**

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/ai-response" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What are the patient'\''s current symptoms and when did they start?"
     }'
```

**Python Example:**
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/chat/ai-response",
    json={"query": "What medications is the patient taking?"}
)

if response.status_code == 200:
    data = response.json()
    print(f"AI Response: {data['response']}")
    print(f"Context Records: {len(data.get('patient_context', []))}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

**JavaScript Example:**
```javascript
async function askAI(query) {
    try {
        const response = await fetch('http://localhost:8000/api/v1/chat/ai-response', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Chat API error:', error);
    }
}

// Usage
askAI("Summarize the patient's condition").then(response => {
    console.log(response.response);
});
```

---

## 2. PDF Upload API

### **POST** `/api/v1/upload/pdf`

Uploads and processes PDF files to extract text, create embeddings, and store in vector database for future chat queries.

---

#### **Request Details**

**Headers:**
```
Content-Type: multipart/form-data
Accept: application/json
```

**Request Body (Form Data):**
- `file` (file, required): PDF file to upload
- `patient_id` (string, optional): Patient identifier for metadata

**Field Specifications:**
- `file`:
  - **Accepted Types**: PDF only (.pdf extension)
  - **Maximum Size**: 10MB (10,485,760 bytes)
  - **Content Requirements**: Must contain extractable text
  - **Validation**: File signature validation, content verification

- `patient_id`:
  - **Description**: Optional patient identifier for record association
  - **Format**: String, no specific pattern required
  - **Usage**: Added to metadata for all generated chunks
  - **Example**: "PATIENT_001", "DOE_JOHN_12345"

---

#### **Processing Pipeline**

The endpoint performs comprehensive PDF processing:

1. **File Validation (0.1-0.5s)**
   - File type verification (.pdf extension)
   - File size check (max 10MB)
   - Empty file detection
   - PDF signature validation

2. **PDF Content Validation (0.2-1.0s)**
   - PDF structure integrity check
   - Text extraction capability verification
   - Corruption detection

3. **Text Extraction (1-5s)**
   - Page-by-page text extraction using PyPDF2
   - Text cleaning and normalization
   - Character encoding handling
   - Metadata preservation

4. **Text Chunking (0.1-0.5s)**
   - Smart text segmentation
   - Chunk size: 1000 characters maximum
   - Overlap: 200 characters between chunks
   - Boundary-aware splitting (sentences/paragraphs)

5. **Embedding Generation (2-10s)**
   - Batch processing using OpenAI `text-embedding-ada-002`
   - Vector dimension: 1536 per chunk
   - Batch size: Up to 2000 chunks per API call
   - Error handling for failed embeddings

6. **Vector Database Storage (1-5s)**
   - Pinecone cloud database storage
   - Batch upsert operations (100 vectors per batch)
   - Metadata enrichment
   - Index updating

---

#### **Response Details**

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "PDF processed successfully. Created 25 text chunks and stored 25 records in vector database.",
  "filename": "patient_medical_report.pdf",
  "extracted_text_length": 18450,
  "chunks_created": 25,
  "timestamp": "2025-09-13T11:35:20.456Z"
}
```

**Response Schema:**
- `success` (boolean): Processing success status
- `message` (string): Detailed processing result message
- `filename` (string): Original uploaded filename
- `extracted_text_length` (integer): Total characters extracted from PDF
- `chunks_created` (integer): Number of text chunks created and stored
- `timestamp` (string): ISO 8601 processing completion timestamp

---

#### **Error Responses**

**400 Bad Request - Invalid File Type:**
```json
{
  "detail": "Only PDF files are allowed"
}
```

**400 Bad Request - Empty File:**
```json
{
  "detail": "Uploaded file is empty"
}
```

**400 Bad Request - Corrupted PDF:**
```json
{
  "detail": "Invalid PDF file or corrupted content"
}
```

**408 Request Timeout:**
```json
{
  "detail": "PDF processing timeout. Please try with a smaller file or try again later."
}
```

**413 Payload Too Large:**
```json
{
  "detail": "File size (15728640 bytes) exceeds maximum allowed size (10485760 bytes)"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "file"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Processing Failure Response (200 OK with success: false):**
```json
{
  "success": false,
  "message": "PDF processing failed: Failed to extract text from PDF",
  "filename": "corrupted_document.pdf",
  "timestamp": "2025-09-13T11:40:15.789Z"
}
```

---

#### **Performance Characteristics**

- **Processing Time**: 5-30 seconds (depending on file size and content)
- **Timeout**: 300 seconds (5 minutes)
- **Memory Usage**: ~100-500MB per file (temporary, during processing)
- **Concurrent Uploads**: Supported with async processing
- **File Size Limits**: 10MB maximum
- **Throughput**: ~1-5 files per minute (depending on size)

---

#### **Metadata Enrichment**

Each stored vector includes comprehensive metadata:

```json
{
  "original_filename": "patient_report.pdf",
  "file_size": 2048576,
  "content_type": "application/pdf",
  "upload_method": "api",
  "patient_id": "PATIENT_001",
  "chunk_index": 5,
  "upload_timestamp": "2025-09-13T11:35:20.456Z",
  "content_type": "pdf_extract",
  "source_file": "patient_report.pdf",
  "content_length": 987
}
```

---

#### **Usage Examples**

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/upload/pdf" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/patient_report.pdf" \
     -F "patient_id=PATIENT_001"
```

**Python Example:**
```python
import requests

with open('patient_report.pdf', 'rb') as pdf_file:
    files = {'file': ('patient_report.pdf', pdf_file, 'application/pdf')}
    data = {'patient_id': 'PATIENT_001'}
    
    response = requests.post(
        'http://localhost:8000/api/v1/upload/pdf',
        files=files,
        data=data
    )
    
    if response.status_code == 200:
        result = response.json()
        if result['success']:
            print(f"✅ Upload successful: {result['message']}")
            print(f"📄 Chunks created: {result['chunks_created']}")
        else:
            print(f"❌ Upload failed: {result['message']}")
    else:
        print(f"🚨 HTTP Error: {response.status_code}")
```

**JavaScript Example (Browser):**
```javascript
async function uploadPDF(file, patientId) {
    const formData = new FormData();
    formData.append('file', file);
    if (patientId) {
        formData.append('patient_id', patientId);
    }
    
    try {
        const response = await fetch('http://localhost:8000/api/v1/upload/pdf', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            console.log(`✅ Upload successful: ${result.chunks_created} chunks created`);
            return result;
        } else {
            console.error(`❌ Upload failed: ${result.message || response.statusText}`);
            throw new Error(result.message || 'Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
        throw error;
    }
}

// Usage with file input
document.getElementById('file-input').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
        try {
            const result = await uploadPDF(file, 'PATIENT_001');
            alert(`Success! Created ${result.chunks_created} text chunks.`);
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    }
});
```

**HTML Form Example:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>PDF Upload</title>
</head>
<body>
    <form action="http://localhost:8000/api/v1/upload/pdf" method="post" enctype="multipart/form-data">
        <div>
            <label for="file">Select PDF file:</label>
            <input type="file" id="file" name="file" accept=".pdf" required>
        </div>
        <div>
            <label for="patient_id">Patient ID (optional):</label>
            <input type="text" id="patient_id" name="patient_id" placeholder="e.g., PATIENT_001">
        </div>
        <button type="submit">Upload PDF</button>
    </form>
</body>
</html>
```

---

## Additional API Endpoints

### **GET** `/api/v1/upload/health`
Health check for upload service dependencies.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "pdf_service": "healthy",
    "openai": "healthy",
    "pinecone": "healthy"
  },
  "configuration": {
    "max_file_size": 10485760,
    "allowed_file_types": ["pdf"]
  }
}
```

### **GET** `/api/v1/upload/stats`
Statistics about uploaded content and vector database.

**Response:**
```json
{
  "success": true,
  "index_stats": {
    "dimension": 1536,
    "index_fullness": 0.1,
    "namespaces": {
      "": {
        "vector_count": 1250
      }
    },
    "total_vector_count": 1250
  },
  "configuration": {
    "max_file_size_mb": 10.0,
    "vector_dimension": 1536,
    "top_k_results": 3
  }
}
```

---

## Integration Workflow

### Typical Usage Pattern:

1. **Upload Patient Documents:**
   ```bash
   # Upload multiple PDFs for a patient
   curl -X POST "http://localhost:8000/api/v1/upload/pdf" \
        -F "file=@medical_history.pdf" \
        -F "patient_id=PATIENT_001"
   
   curl -X POST "http://localhost:8000/api/v1/upload/pdf" \
        -F "file=@lab_results.pdf" \
        -F "patient_id=PATIENT_001"
   ```

2. **Query Patient Information:**
   ```bash
   # Ask questions about the uploaded documents
   curl -X POST "http://localhost:8000/api/v1/chat/ai-response" \
        -H "Content-Type: application/json" \
        -d '{"query": "What are the latest lab results for this patient?"}'
   ```

3. **Monitor System Health:**
   ```bash
   # Check if all services are operational
   curl -X GET "http://localhost:8000/health"
   ```

This comprehensive API enables building sophisticated medical chat applications with document-based context awareness and intelligent response generation.