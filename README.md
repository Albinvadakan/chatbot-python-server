# Chatbot Python Server

A comprehensive FastAPI-based chatbot server with PDF processing capabilities and vector database integration using Pinecone and OpenAI.

## 🚀 Features

- **🤖 AI Chat API**: Intelligent responses using OpenAI GPT with patient context
- **📄 PDF Processing**: Extract text from PDFs and store in vector database
- **🔍 Vector Search**: Semantic search through patient history using embeddings
- **⚡ Fast API**: High-performance async API with automatic documentation
- **🧠 LangChain Integration**: Advanced language model operations
- **📊 Comprehensive Logging**: Structured JSON logging for monitoring
- **🛡️ Error Handling**: Robust error handling with detailed responses
- **📈 Health Checks**: Built-in health monitoring endpoints

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client App    │────│   FastAPI       │────│   OpenAI        │
│                 │    │   Server        │    │   API           │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        
                       ┌─────────────────┐    ┌─────────────────┐
                       │   PDF Service   │────│   Pinecone      │
                       │   (PyPDF2)      │    │   Vector DB     │
                       └─────────────────┘    └─────────────────┘
```

## 📁 Project Structure

```
chatbot-python-server/
├── app/
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models and schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py            # Chat API endpoints
│   │   └── upload.py          # PDF upload endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── openai_service.py   # OpenAI integration
│   │   ├── pinecone_service.py # Vector database operations
│   │   └── pdf_service.py      # PDF processing logic
│   ├── config.py              # Configuration management
│   ├── main.py                # FastAPI application
│   └── utils.py               # Error handling and logging
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables
├── .gitignore                # Git ignore file
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker Compose setup
├── start.sh                  # Linux/Mac startup script
├── start.bat                 # Windows startup script
├── test_api.py              # API testing script
└── README.md                # This file
```

## 🚀 Quick Start

### Option 1: Local Development

1. **Clone and setup:**
```bash
git clone <your-repo>
cd chatbot-python-server
```

2. **Create virtual environment:**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
Copy `.env` file and update with your API keys:
```env
OPENAI_API_KEY=your_openai_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=your_pinecone_environment_here
PINECONE_INDEX_NAME=your_pinecone_index_name_here
```

5. **Run the server:**
```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh
./start.sh

# Or directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Docker

1. **Using Docker Compose:**
```bash
# Make sure .env file is configured
docker-compose up --build
```

2. **Using Docker only:**
```bash
docker build -t chatbot-server .
docker run -p 8000:8000 --env-file .env chatbot-server
```

## 📚 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔌 API Endpoints

### Chat Endpoints
- `POST /api/v1/chat/ai-response` - Generate AI response with context
- `GET /api/v1/chat/health` - Chat service health check

### Upload Endpoints
- `POST /api/v1/upload/pdf` - Upload and process PDF files
- `GET /api/v1/upload/health` - Upload service health check
- `GET /api/v1/upload/stats` - Vector database statistics

### System Endpoints
- `GET /` - Root endpoint with basic info
- `GET /health` - Comprehensive health check
- `GET /config` - Public configuration information

## 📋 Example Usage

### Chat API
```bash
curl -X POST "http://localhost:8000/api/v1/chat/ai-response" \
     -H "Content-Type: application/json" \
     -d '{"query": "What are the symptoms of diabetes?"}'
```

### PDF Upload
```bash
curl -X POST "http://localhost:8000/api/v1/upload/pdf" \
     -F "file=@sample.pdf" \
     -F "patient_id=patient_123"
```

### Testing Script
```bash
python test_api.py
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Yes | - |
| `PINECONE_API_KEY` | Pinecone API key | Yes | - |
| `PINECONE_ENVIRONMENT` | Pinecone environment | Yes | - |
| `PINECONE_INDEX_NAME` | Pinecone index name | Yes | - |
| `APP_NAME` | Application name | No | "Chatbot Python Server" |
| `DEBUG` | Enable debug mode | No | False |
| `LOG_LEVEL` | Logging level | No | INFO |
| `HOST` | Server host | No | 0.0.0.0 |
| `PORT` | Server port | No | 8000 |
| `MAX_FILE_SIZE` | Max PDF file size | No | 10MB |
| `MAX_TOKENS` | OpenAI max tokens | No | 1000 |
| `TEMPERATURE` | OpenAI temperature | No | 0.7 |

### Pinecone Setup

1. **Create a Pinecone account** at https://pinecone.io
2. **Create an index** with:
   - Dimensions: 1536 (for OpenAI ada-002 embeddings)
   - Metric: cosine
   - Pod type: Starter (or your preferred type)
3. **Get your API key** from the Pinecone console
4. **Note your environment** (e.g., "us-west1-gcp")

### OpenAI Setup

1. **Create an OpenAI account** at https://openai.com
2. **Generate an API key** from the API section
3. **Ensure you have sufficient credits** for embeddings and chat completions

## 🐛 Troubleshooting

### Common Issues

1. **"Index not found" error:**
   - Ensure your Pinecone index exists
   - Check index name in environment variables
   - Verify API key permissions

2. **OpenAI API errors:**
   - Check API key validity
   - Verify sufficient credits
   - Check rate limits

3. **PDF processing fails:**
   - Ensure file is a valid PDF
   - Check file size limits
   - Verify PDF is not password protected

### Debugging

Enable debug mode:
```env
DEBUG=True
LOG_LEVEL=DEBUG
```

Check logs for detailed error information.

## 🔒 Security Considerations

- **API Keys**: Never commit API keys to version control
- **CORS**: Configure CORS appropriately for production
- **Authentication**: Implement authentication for production use
- **Rate Limiting**: Add rate limiting to prevent abuse
- **File Validation**: Validate uploaded files thoroughly
- **Input Sanitization**: Sanitize all user inputs

## 🚀 Production Deployment

### Considerations

1. **Use environment variables** for all configuration
2. **Implement proper logging** and monitoring
3. **Add authentication** and authorization
4. **Set up rate limiting**
5. **Configure CORS** for your domain
6. **Use HTTPS** in production
7. **Monitor resource usage** and scale as needed

### Recommended Stack

- **Container**: Docker + Kubernetes
- **Reverse Proxy**: Nginx
- **Load Balancer**: AWS ALB or similar
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or similar

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with details