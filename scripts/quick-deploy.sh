#!/bin/bash

# Quick Deployment Script
# This script provides a simple way to deploy the TikTok API

set -e

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

# Show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -e, --env FILE          Environment file (default: .env)"
    echo "  -t, --tag TAG           Docker tag (default: latest)"
    echo "  -s, --skip-build        Skip building the image"
    echo "  -p, --push-only         Only push the image (skip deployment)"
    echo "  --setup-server          Run server setup script"
    echo ""
    echo "Examples:"
    echo "  $0                      # Deploy with default settings"
    echo "  $0 -t v1.0.0           # Deploy with specific tag"
    echo "  $0 --setup-server      # Setup server environment"
    echo "  $0 -p                  # Only push image to Docker Hub"
}

# Parse command line arguments
ENV_FILE=".env"
DOCKER_TAG="latest"
SKIP_BUILD=false
PUSH_ONLY=false
SETUP_SERVER=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -e|--env)
            ENV_FILE="$2"
            shift 2
            ;;
        -t|--tag)
            DOCKER_TAG="$2"
            shift 2
            ;;
        -s|--skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -p|--push-only)
            PUSH_ONLY=true
            shift
            ;;
        --setup-server)
            SETUP_SERVER=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Load environment variables
load_env() {
    if [[ -f "$ENV_FILE" ]]; then
        log_info "Loading environment from $ENV_FILE"
        export $(grep -v '^#' "$ENV_FILE" | xargs)
    else
        log_warning "Environment file $ENV_FILE not found"
        log_info "Please create $ENV_FILE with your configuration"
        log_info "You can use env.deployment.example as a template"
        exit 1
    fi
}

# Setup server
setup_server() {
    log_info "Setting up server..."
    
    if [[ -z "$SERVER_HOST" ]]; then
        log_error "SERVER_HOST not set in environment file"
        exit 1
    fi
    
    # Copy setup script to server and run it
    scp -P ${SERVER_PORT:-22} scripts/server-setup.sh ${SERVER_USERNAME}@${SERVER_HOST}:/tmp/
    ssh -p ${SERVER_PORT:-22} ${SERVER_USERNAME}@${SERVER_HOST} "chmod +x /tmp/server-setup.sh && /tmp/server-setup.sh"
    
    log_success "Server setup completed"
}

# Build image
build_image() {
    if [[ "$SKIP_BUILD" == "true" ]]; then
        log_info "Skipping build (--skip-build flag used)"
        return
    fi
    
    log_info "Building Docker image with tag: $DOCKER_TAG"
    
    if [[ -z "$DOCKER_USERNAME" ]]; then
        log_error "DOCKER_USERNAME not set in environment file"
        exit 1
    fi
    
    docker build -t "${DOCKER_USERNAME}/tik-tok-api:${DOCKER_TAG}" .
    
    if [[ $? -eq 0 ]]; then
        log_success "Docker image built successfully"
    else
        log_error "Failed to build Docker image"
        exit 1
    fi
}

# Push image
push_image() {
    log_info "Pushing image to Docker Hub..."
    
    # Login to Docker Hub if needed
    if ! docker info | grep -q "Username"; then
        log_info "Logging in to Docker Hub..."
        echo "$DOCKER_PASSWORD" | docker login --username "$DOCKER_USERNAME" --password-stdin
    fi
    
    docker push "${DOCKER_USERNAME}/tik-tok-api:${DOCKER_TAG}"
    
    if [[ $? -eq 0 ]]; then
        log_success "Image pushed to Docker Hub successfully"
    else
        log_error "Failed to push image to Docker Hub"
        exit 1
    fi
}

# Deploy to server
deploy_to_server() {
    if [[ "$PUSH_ONLY" == "true" ]]; then
        log_info "Skipping deployment (--push-only flag used)"
        return
    fi
    
    log_info "Deploying to server..."
    
    # Copy docker-compose file to server
    log_info "Copying docker-compose.prod.yml to server..."
    scp -P ${SERVER_PORT:-22} docker-compose.prod.yml ${SERVER_USERNAME}@${SERVER_HOST}:/opt/tik-tok-api/
    
    # Create deployment script
    cat > /tmp/deploy_remote.sh << EOF
#!/bin/bash
set -e

cd /opt/tik-tok-api || { mkdir -p /opt/tik-tok-api && cd /opt/tik-tok-api; }

# Set environment variables for docker-compose
export DOCKER_USERNAME="${DOCKER_USERNAME}"
export API_KEYS="${API_KEYS}"
export MS_TOKENS="${MS_TOKENS}"
export REDIS_URL="${REDIS_URL}"
export LOG_LEVEL="INFO"

echo "Pulling latest image..."
docker pull ${DOCKER_USERNAME}/tiktok-api:${DOCKER_TAG}

echo "Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down || true

echo "Starting services with docker-compose..."
docker-compose -f docker-compose.prod.yml up -d

echo "Waiting for containers to start..."
sleep 15

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

    # Copy and execute deployment script
    scp -P ${SERVER_PORT:-22} /tmp/deploy_remote.sh ${SERVER_USERNAME}@${SERVER_HOST}:/tmp/
    ssh -p ${SERVER_PORT:-22} ${SERVER_USERNAME}@${SERVER_HOST} "chmod +x /tmp/deploy_remote.sh && /tmp/deploy_remote.sh"
    
    # Clean up
    rm /tmp/deploy_remote.sh
    
    log_success "Deployment completed successfully"
}

# Health check
health_check() {
    if [[ "$PUSH_ONLY" == "true" ]]; then
        return
    fi
    
    log_info "Performing health check..."
    sleep 30
    
    if curl -f "http://${SERVER_HOST}:8000/health" > /dev/null 2>&1; then
        log_success "Health check passed - service is running"
        log_info "Service URL: http://${SERVER_HOST}:8000"
        log_info "API Documentation: http://${SERVER_HOST}:8000/docs"
    else
        log_warning "Health check failed - service might not be ready yet"
        log_info "You can check manually at: http://${SERVER_HOST}:8000/health"
    fi
}

# Main function
main() {
    log_info "Starting TikTok API deployment..."
    log_info "Docker tag: $DOCKER_TAG"
    
    load_env
    
    if [[ "$SETUP_SERVER" == "true" ]]; then
        setup_server
        exit 0
    fi
    
    build_image
    push_image
    deploy_to_server
    health_check
    
    log_success "🎉 Deployment completed successfully!"
}

# Run main function
main "$@"
