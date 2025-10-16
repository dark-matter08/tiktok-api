#!/bin/bash

# TikTok API Deployment Script
# Usage: ./scripts/deploy.sh [environment] [version]

set -e

# Configuration
DOCKER_IMAGE="tik-tok-api"
DOCKER_USERNAME="${DOCKER_USERNAME:-}"
DOCKER_TAG="${1:-latest}"
ENVIRONMENT="${2:-production}"
SERVER_HOST="${SERVER_HOST:-}"
SERVER_USERNAME="${SERVER_USERNAME:-}"
SERVER_PORT="${SERVER_PORT:-22}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required environment variables are set
check_requirements() {
    log_info "Checking requirements..."
    
    if [[ -z "$DOCKER_USERNAME" ]]; then
        log_error "DOCKER_USERNAME environment variable is required"
        exit 1
    fi
    
    if [[ -z "$SERVER_HOST" ]]; then
        log_error "SERVER_HOST environment variable is required"
        exit 1
    fi
    
    if [[ -z "$SERVER_USERNAME" ]]; then
        log_error "SERVER_USERNAME environment variable is required"
        exit 1
    fi
    
    log_success "Requirements check passed"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    # Build the image
    docker build -t "${DOCKER_USERNAME}/${DOCKER_IMAGE}:${DOCKER_TAG}" .
    
    if [[ $? -eq 0 ]]; then
        log_success "Docker image built successfully"
    else
        log_error "Failed to build Docker image"
        exit 1
    fi
}

# Push image to Docker Hub
push_image() {
    log_info "Pushing image to Docker Hub..."
    
    # Login to Docker Hub (if not already logged in)
    if ! docker info | grep -q "Username"; then
        log_info "Logging in to Docker Hub..."
        docker login
    fi
    
    # Push the image
    docker push "${DOCKER_USERNAME}/${DOCKER_IMAGE}:${DOCKER_TAG}"
    
    if [[ $? -eq 0 ]]; then
        log_success "Image pushed to Docker Hub successfully"
    else
        log_error "Failed to push image to Docker Hub"
        exit 1
    fi
}

# Deploy to server
deploy_to_server() {
    log_info "Deploying to server ${SERVER_HOST}..."
    
    # Copy docker-compose file to server
    log_info "Copying docker-compose.prod.yml to server..."
    scp -P ${SERVER_PORT} docker-compose.prod.yml ${SERVER_USERNAME}@${SERVER_HOST}:/opt/tik-tok-api/
    
    # Create deployment script
    cat > /tmp/deploy_remote.sh << EOF
#!/bin/bash
set -e

# Navigate to deployment directory
cd /opt/tik-tok-api || { mkdir -p /opt/tik-tok-api && cd /opt/tik-tok-api; }

# Set environment variables for docker-compose
export DOCKER_USERNAME="${DOCKER_USERNAME}"
export API_KEYS="${API_KEYS}"
export MS_TOKENS="${MS_TOKENS}"
export REDIS_URL="${REDIS_URL}"
export LOG_LEVEL="INFO"

# Pull latest image
echo "Pulling latest image..."
docker pull ${DOCKER_USERNAME}/${DOCKER_IMAGE}:${DOCKER_TAG}

# Stop and remove existing containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down || true

# Start services with docker-compose
echo "Starting services with docker-compose..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for containers to start
echo "Waiting for containers to start..."
sleep 15

# Check if containers are running
if docker ps | grep -q tik-tok-api-backend; then
    echo "✅ Deployment successful!"
    echo "Running containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo "API container logs:"
    docker logs --tail 20 tik-tok-api-backend
else
    echo "❌ Deployment failed!"
    echo "Container status:"
    docker ps -a | grep tik-tok
    echo "API container logs:"
    docker logs tik-tok-api-backend
    exit 1
fi
EOF

    # Copy deployment script to server and execute
    scp -P ${SERVER_PORT} /tmp/deploy_remote.sh ${SERVER_USERNAME}@${SERVER_HOST}:/tmp/
    ssh -p ${SERVER_PORT} ${SERVER_USERNAME}@${SERVER_HOST} "chmod +x /tmp/deploy_remote.sh && /tmp/deploy_remote.sh"
    
    # Clean up
    rm /tmp/deploy_remote.sh
    
    log_success "Deployment completed successfully"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Wait a bit for the service to be ready
    sleep 30
    
    # Check if the service is responding
    if curl -f "http://${SERVER_HOST}:8000/health" > /dev/null 2>&1; then
        log_success "Health check passed - service is running"
    else
        log_warning "Health check failed - service might not be ready yet"
        log_info "You can check the service manually at: http://${SERVER_HOST}:8000/health"
    fi
}

# Main deployment function
main() {
    log_info "Starting deployment process..."
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Docker tag: ${DOCKER_TAG}"
    log_info "Server: ${SERVER_USERNAME}@${SERVER_HOST}:${SERVER_PORT}"
    
    check_requirements
    build_image
    push_image
    deploy_to_server
    health_check
    
    log_success "🎉 Deployment completed successfully!"
    log_info "Service URL: http://${SERVER_HOST}:8000"
    log_info "API Documentation: http://${SERVER_HOST}:8000/docs"
}

# Run main function
main "$@"
