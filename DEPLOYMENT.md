# Deployment Guide

This guide covers different deployment options for the Chatbot Python Server.

## 🐳 Docker Deployment

### Prerequisites
- Docker and Docker Compose installed
- Configured `.env` file

### Steps

1. **Build and run with Docker Compose:**
```bash
docker-compose up --build -d
```

2. **Check container status:**
```bash
docker-compose ps
```

3. **View logs:**
```bash
docker-compose logs -f chatbot-api
```

4. **Stop services:**
```bash
docker-compose down
```

## ☁️ Cloud Deployment

### AWS ECS

1. **Create ECR repository:**
```bash
aws ecr create-repository --repository-name chatbot-python-server
```

2. **Build and push Docker image:**
```bash
# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t chatbot-python-server .

# Tag image
docker tag chatbot-python-server:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/chatbot-python-server:latest

# Push image
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/chatbot-python-server:latest
```

3. **Create ECS task definition with environment variables**

### Google Cloud Run

1. **Build and deploy:**
```bash
gcloud builds submit --tag gcr.io/[PROJECT-ID]/chatbot-python-server
gcloud run deploy --image gcr.io/[PROJECT-ID]/chatbot-python-server --platform managed
```

### Azure Container Instances

1. **Create resource group:**
```bash
az group create --name chatbot-rg --location eastus
```

2. **Deploy container:**
```bash
az container create \
  --resource-group chatbot-rg \
  --name chatbot-python-server \
  --image your-registry/chatbot-python-server:latest \
  --cpu 1 \
  --memory 2 \
  --ports 8000 \
  --environment-variables OPENAI_API_KEY=xxx PINECONE_API_KEY=xxx
```

## 🖥️ VPS/Dedicated Server

### Using systemd (Linux)

1. **Create systemd service file:**
```bash
sudo nano /etc/systemd/system/chatbot.service
```

2. **Service configuration:**
```ini
[Unit]
Description=Chatbot Python Server
After=network.target

[Service]
Type=exec
User=chatbot
WorkingDirectory=/home/chatbot/chatbot-python-server
Environment=PATH=/home/chatbot/chatbot-python-server/venv/bin
ExecStart=/home/chatbot/chatbot-python-server/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. **Enable and start service:**
```bash
sudo systemctl enable chatbot
sudo systemctl start chatbot
sudo systemctl status chatbot
```

### Using PM2 (Node.js process manager)

1. **Install PM2:**
```bash
npm install -g pm2
```

2. **Create ecosystem file:**
```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'chatbot-python-server',
    script: 'venv/bin/uvicorn',
    args: 'app.main:app --host 0.0.0.0 --port 8000',
    interpreter: 'none',
    instances: 1,
    exec_mode: 'fork',
    watch: false,
    env: {
      NODE_ENV: 'production'
    }
  }]
};
```

3. **Start with PM2:**
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

## 🔧 Production Configuration

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL with Let's Encrypt

```bash
sudo certbot --nginx -d your-domain.com
```

### Environment Variables for Production

```env
# Production settings
DEBUG=False
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Security
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_FILE_TYPES=["pdf"]

# Performance
MAX_TOKENS=1500
TEMPERATURE=0.5
TOP_K_RESULTS=5
```

## 📊 Monitoring

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

HEALTH_URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "Service is healthy"
    exit 0
else
    echo "Service is unhealthy (HTTP: $RESPONSE)"
    exit 1
fi
```

### Log Monitoring

```bash
# Monitor logs
tail -f /var/log/chatbot/app.log

# With Docker
docker-compose logs -f chatbot-api

# Search for errors
grep ERROR /var/log/chatbot/app.log
```

## 🔐 Security Checklist

- [ ] Environment variables properly set
- [ ] API keys not in code/logs
- [ ] HTTPS enabled
- [ ] CORS properly configured
- [ ] Rate limiting implemented
- [ ] File upload validation
- [ ] Regular security updates
- [ ] Monitoring and alerting setup
- [ ] Backup strategy in place

## 🚨 Troubleshooting

### Common Issues

1. **Service won't start:**
   - Check environment variables
   - Verify API keys
   - Check port availability
   - Review logs

2. **High memory usage:**
   - Monitor Pinecone operations
   - Check for memory leaks
   - Optimize chunk sizes

3. **Slow responses:**
   - Check OpenAI API latency
   - Optimize vector search
   - Add caching if needed

### Performance Tuning

1. **Optimize worker count:**
```bash
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
```

2. **Use Gunicorn for production:**
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

3. **Configure connection pools:**
   - Adjust OpenAI client settings
   - Optimize Pinecone connections

## 📞 Support

For deployment issues:
1. Check logs first
2. Verify configuration
3. Test connectivity
4. Review security settings
5. Contact support with details