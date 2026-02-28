# Production Deployment Guide

## Architecture Overview

This project follows the standardized production architecture template:

- **Port**: 8010 (inventory manager project)
- **Server Path**: `/srv/inventory_manager`
- **Docker**: Production containerization with gunicorn
- **Systemd**: Service management for persistence
- **Nginx**: Reverse proxy routing
- **CI/CD**: GitHub Actions automated deployment

## Production Files

### Docker Configuration
- `Dockerfile` - Production container with Python 3.11, gunicorn, non-root user
- `docker-compose.yml` - Service definition with port 8010 mapping

### System Services
- `inventory_manager.service` - systemd service file for auto-restart
- `nginx-inventory-manager.conf` - Nginx location block for `/inventory/` route

### CI/CD
- `.github/workflows/deploy.yml` - Automated deployment pipeline

## Deployment Setup

### 1. Server Preparation
```bash
# On production server
sudo mkdir -p /srv/inventory_manager
sudo chown lex:lex /srv/inventory_manager
cd /srv/inventory_manager
git clone <repository-url> .
```

### 2. Systemd Service Installation
```bash
sudo cp inventory_manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable inventory_manager.service
sudo systemctl start inventory_manager.service
```

### 3. Nginx Configuration
```bash
# Add the contents of nginx-inventory-manager.conf to your main nginx config
# Usually in /etc/nginx/sites-available/default or similar
sudo systemctl reload nginx
```

### 4. GitHub Secrets Configuration
Required repository secrets:
- `HOST_IP` - Production server IP address
- `SSH_USERNAME` - SSH user (usually 'lex')
- `SSH_KEY` - Private SSH key for server access

## Service Management

### Start/Stop/Restart
```bash
sudo systemctl start inventory_manager.service
sudo systemctl stop inventory_manager.service
sudo systemctl restart inventory_manager.service
```

### View Logs
```bash
sudo systemctl status inventory_manager.service
sudo journalctl -u inventory_manager.service -f
docker compose logs -f
```

### Manual Deployment
```bash
cd /srv/inventory_manager
git pull origin main
docker compose down
docker compose up -d --build
sudo systemctl restart inventory_manager.service
```

## URL Access

Once deployed, the application will be accessible at:
`https://yourdomain.com/inventory/`

The Nginx reverse proxy routes this to the internal Docker container on port 8010.