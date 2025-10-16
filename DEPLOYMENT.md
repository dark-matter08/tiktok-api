# TikTok API Deployment Guide

This guide covers how to deploy the TikTok API backend to your server using Docker and automated deployment pipelines.

## 🚀 Quick Start

### 1. Setup Server Environment

First, set up your server with the required dependencies:

```bash
# Copy the setup script to your server and run it
scp scripts/server-setup.sh user@your-server:/tmp/
ssh user@your-server "chmod +x /tmp/server-setup.sh && /tmp/server-setup.sh"
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cp env.deployment.example .env
```

Edit `.env` with your actual values:

```bash
# Docker Hub Configuration
DOCKER_USERNAME=your-dockerhub-username
DOCKER_PASSWORD=your-dockerhub-password

# Server Configuration
SERVER_HOST=your-server-ip-or-domain
SERVER_USERNAME=your-server-username
SERVER_PORT=22

# API Configuration
API_KEYS=your-api-key-1,your-api-key-2,your-api-key-3
MS_TOKENS=your-ms-token-1,your-ms-token-2

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379
```

### 3. Deploy

Use the quick deployment script:

```bash
# Deploy with default settings
./scripts/quick-deploy.sh

# Deploy with specific tag
./scripts/quick-deploy.sh -t v1.0.0

# Setup server first (if not done already)
./scripts/quick-deploy.sh --setup-server
```

## 🔧 Manual Deployment

### Build and Push Image

```bash
# Build the image
docker build -t your-username/tik-tok-api:latest .

# Push to Docker Hub
docker push your-username/tik-tok-api:latest
```

### Deploy to Server

```bash
# SSH into your server
ssh user@your-server

# Copy docker-compose file to server
scp docker-compose.prod.yml user@your-server:/opt/tik-tok-api/

# Set environment variables
export DOCKER_USERNAME="your-username"
export API_KEYS="your-api-key-1,your-api-key-2"
export MS_TOKENS="your-ms-token-1,your-ms-token-2"
export REDIS_URL="redis://localhost:6379"
export LOG_LEVEL="INFO"

# Navigate to deployment directory
cd /opt/tik-tok-api

# Pull latest image
docker pull your-username/tiktok-api:latest

# Stop existing containers
docker-compose -f docker-compose.prod.yml down || true

# Start services with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

## 🤖 Automated Deployment with GitHub Actions

### 1. Set up GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions, and add:

- `DOCKER_USERNAME`: Your Docker Hub username
- `DOCKER_PASSWORD`: Your Docker Hub password/token
- `SERVER_HOST`: Your server IP or domain
- `SERVER_USERNAME`: Your server username
- `SERVER_SSH_KEY`: Your private SSH key
- `SERVER_PORT`: SSH port (default: 22)
- `API_KEYS`: Your API keys (comma-separated)
- `MS_TOKENS`: Your MS tokens (comma-separated)
- `REDIS_URL`: Redis connection string (optional)

### 2. Push to Main Branch

The deployment pipeline will automatically trigger when you push to the `main` or `master` branch:

```bash
git add .
git commit -m "Deploy new version"
git push origin main
```

### 3. Monitor Deployment

Check the GitHub Actions tab in your repository to monitor the deployment progress.

## 🐳 Docker Compose Deployment

For a more complete setup with Redis and Nginx:

```bash
# Copy environment file
cp env.deployment.example .env

# Edit with your values
nano .env

# Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 Monitoring and Health Checks

### Health Check

```bash
curl http://your-server:8000/health
```

### View Logs

```bash
# On the server
docker logs tik-tok-api-backend

# Follow logs in real-time
docker logs -f tik-tok-api-backend
```

### Container Status

```bash
docker ps | grep tik-tok-api
```

## 🔄 Update Deployment

### Using Quick Deploy Script

```bash
# Update to latest version
./scripts/quick-deploy.sh

# Update to specific version
./scripts/quick-deploy.sh -t v1.2.0
```

### Using GitHub Actions

Simply push to the main branch - the pipeline will handle the rest.

### Manual Update

```bash
# On the server
cd /opt/tik-tok-api

# Set environment variables
export DOCKER_USERNAME="your-username"
export API_KEYS="your-api-key-1,your-api-key-2"
export MS_TOKENS="your-ms-token-1,your-ms-token-2"
export REDIS_URL="redis://localhost:6379"
export LOG_LEVEL="INFO"

# Pull latest image
docker pull your-username/tiktok-api:latest

# Stop existing containers
docker-compose -f docker-compose.prod.yml down

# Start services with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

## 🛠️ Troubleshooting

### Container Won't Start

1. Check logs: `docker logs tik-tok-api-backend`
2. Verify environment variables are set correctly
3. Ensure ports are not already in use: `netstat -tulpn | grep 8000`

### Health Check Fails

1. Wait a few minutes for the service to fully start
2. Check if Playwright browsers are installed: `docker exec tik-tok-api-backend ls -la /home/appuser/.cache/ms-playwright/`
3. Verify API keys and MS tokens are valid

### Connection Issues

1. Check firewall settings: `sudo ufw status`
2. Verify the service is listening: `docker exec tik-tok-api-backend netstat -tulpn`
3. Test local connection: `curl http://localhost:8000/health`

## 🔐 Security Considerations

1. **Use strong API keys**: Generate secure, random API keys
2. **Rotate MS tokens**: Regularly update your MS tokens
3. **Firewall**: Only expose necessary ports (22, 80, 443, 8000)
4. **SSL/TLS**: Use HTTPS in production with proper certificates
5. **Updates**: Keep your server and Docker images updated

## 📝 Environment Variables Reference

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `API_KEYS` | Comma-separated API keys for authentication | Yes | - |
| `MS_TOKENS` | Comma-separated MS tokens for TikTok API | Yes | - |
| `ENVIRONMENT` | Environment (development/production) | No | development |
| `REDIS_URL` | Redis connection string | No | - |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | No | INFO |
| `TIKTOK_NUM_SESSIONS` | Number of TikTok sessions | No | 1 |
| `TIKTOK_SLEEP_AFTER` | Sleep time after requests | No | 1 |
| `TIKTOK_BROWSER` | Browser type for Playwright | No | chromium |

## 🎯 Production Checklist

- [ ] Server setup completed
- [ ] Environment variables configured
- [ ] Docker image built and pushed
- [ ] Container deployed and running
- [ ] Health check passing
- [ ] Firewall configured
- [ ] SSL certificate installed (if using HTTPS)
- [ ] Monitoring set up
- [ ] Backup strategy in place
- [ ] Documentation updated

## 📞 Support

If you encounter issues:

1. Check the logs: `docker logs tik-tok-api-backend`
2. Verify your configuration
3. Test with a simple curl request
4. Check the GitHub Issues for known problems

For additional help, refer to the main README.md file.
