# Professional Inventory Management System - Docker Deployment

A production-ready inventory management system designed for retail operations with Lightspeed X-Series integration.

## 🚀 Production Deployment

Deploy the containerized application:

```bash
docker run -p 8010:8010 \
  -e GOOGLE_SHEET_NAME="Live ATS Inventory" \
  -e LS_X_API_TOKEN="your_token" \
  -e LS_ACCOUNT_DOMAIN="your_domain" \
  inventory-manager
```

Then access the application at: **http://localhost:8010**

---

## 📦 Deployment Instructions

### Prerequisites
- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Google Sheets API credentials
- Lightspeed X-Series API access

### Build the Production Image

```bash
# Build the production image
docker build -f deploy/docker/Dockerfile -t inventory-manager .

# Run with environment configuration
docker run -p 8010:8010 \
  --env-file .env \
  inventory-manager
```

### Environment Configuration

Create a `.env` file based on `.env.example`:

```bash
# Required for production
GOOGLE_SERVICE_ACCOUNT_JSON=./service_account.json
GOOGLE_SHEET_NAME=Live ATS Inventory
LS_X_API_TOKEN=your_lightspeed_api_token
LS_ACCOUNT_DOMAIN=your_account_domain

# Application settings
FLASK_ENV=production
PORT=8010
SECRET_KEY=your_secure_secret_key
```

## 🏗️ Production Architecture

### Container Specifications
- **Base Image**: python:3.11-slim
- **Runtime**: Gunicorn WSGI server
- **Port**: 8010
- **Security**: Non-root user execution
- **Size**: ~200MB optimized

### Key Features
- **Lightspeed Integration**: Real-time inventory synchronization
- **Google Sheets**: Operations dashboard and reporting
- **Automated Scheduling**: Hourly inventory updates
- **Production Security**: Secure configuration management
- **Health Monitoring**: Built-in health check endpoints

### Service Architecture
1. **Flask Application** - Core inventory management
2. **Scheduler Service** - Automated synchronization
3. **Google Sheets API** - Operations integration
4. **Lightspeed API** - POS system connectivity

## 🔧 Configuration Management

### Volume Mounting
```bash
# Mount configuration and logs
docker run -p 8010:8010 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  inventory-manager
```

### Service Account Setup
```bash
# Mount Google service account credentials
docker run -p 8010:8010 \
  -v $(pwd)/service_account.json:/app/service_account.json \
  -e GOOGLE_SERVICE_ACCOUNT_JSON=/app/service_account.json \
  inventory-manager
```

## 🔍 Health Monitoring

### Health Check Endpoint
```bash
curl http://localhost:8010/health
# Returns: {"status": "ok", "sheets_configured": true}
```

### Application Metrics
- **Inventory Status**: Real-time stock levels
- **Sync Status**: Last synchronization timestamp  
- **System Health**: Application and service status

## 🛡️ Security Considerations

- Secure secret management via environment variables
- Non-root container execution
- API token encryption and secure storage
- Network security with proper port exposure

## 🏭 Production Deployment

For production environments, use with:
- **Reverse Proxy**: Nginx configuration included
- **Service Management**: systemd service files
- **CI/CD**: GitHub Actions workflow
- **Monitoring**: Built-in health checks

See [DEPLOYMENT.md](../../DEPLOYMENT.md) for complete production setup.

## 📝 License

Proprietary - Portfolio Project
