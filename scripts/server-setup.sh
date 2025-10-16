#!/bin/bash

# Server Setup Script for TikTok API
# This script sets up the server environment for deployment

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

# Update system packages
update_system() {
    log_info "Updating system packages..."
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get upgrade -y
    elif command -v yum &> /dev/null; then
        sudo yum update -y
    elif command -v dnf &> /dev/null; then
        sudo dnf update -y
    else
        log_warning "Package manager not recognized. Please update manually."
    fi
    
    log_success "System packages updated"
}

# Install Docker
install_docker() {
    log_info "Installing Docker..."
    
    if command -v docker &> /dev/null; then
        log_info "Docker is already installed"
        return
    fi
    
    # Install Docker using the official script
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    # Start and enable Docker service
    sudo systemctl start docker
    sudo systemctl enable docker
    
    log_success "Docker installed successfully"
    log_warning "Please log out and log back in for Docker group changes to take effect"
}

# Install Docker Compose
install_docker_compose() {
    log_info "Installing Docker Compose..."
    
    if command -v docker-compose &> /dev/null; then
        log_info "Docker Compose is already installed"
        return
    fi
    
    # Get latest version
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    
    # Download and install
    sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    log_success "Docker Compose installed successfully"
}

# Create deployment directory
create_deployment_directory() {
    log_info "Creating deployment directory..."
    
    sudo mkdir -p /opt/tik-tok-api
    sudo chown $USER:$USER /opt/tik-tok-api
    
    log_success "Deployment directory created at /opt/tik-tok-api"
}

# Configure firewall
configure_firewall() {
    log_info "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian with UFW
        sudo ufw allow 22/tcp   # SSH
        sudo ufw allow 8000/tcp # TikTok API
        sudo ufw --force enable
        log_success "UFW firewall configured"
    elif command -v firewall-cmd &> /dev/null; then
        # CentOS/RHEL with firewalld
        sudo firewall-cmd --permanent --add-port=22/tcp
        sudo firewall-cmd --permanent --add-port=8000/tcp
        sudo firewall-cmd --reload
        log_success "Firewalld configured"
    else
        log_warning "No firewall detected. Please configure manually if needed."
    fi
}

# Install monitoring tools
install_monitoring() {
    log_info "Installing monitoring tools..."
    
    # Install htop for process monitoring
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y htop curl wget
    elif command -v yum &> /dev/null; then
        sudo yum install -y htop curl wget
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y htop curl wget
    fi
    
    log_success "Monitoring tools installed"
}

# Create systemd service (optional)
create_systemd_service() {
    log_info "Creating systemd service..."
    
    sudo tee /etc/systemd/system/tik-tok-api.service > /dev/null << EOF
[Unit]
Description=TikTok API Backend
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/tik-tok-api
ExecStart=/usr/bin/docker run -d --name tik-tok-api-backend --restart unless-stopped -p 8000:8000 -e ENVIRONMENT=production YOUR_DOCKER_USERNAME/tik-tok-api:latest
ExecStop=/usr/bin/docker stop tik-tok-api-backend
ExecStopPost=/usr/bin/docker rm tik-tok-api-backend
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    log_success "Systemd service created (disabled by default)"
    log_info "To enable: sudo systemctl enable tik-tok-api.service"
}

# Create deployment script on server
create_deployment_script() {
    log_info "Creating deployment script on server..."
    
    cat > /opt/tik-tok-api/deploy.sh << 'EOF'
#!/bin/bash
# Server-side deployment script

set -e

DOCKER_IMAGE="tiktok-api"
DOCKER_USERNAME="${DOCKER_USERNAME}"
DOCKER_TAG="${1:-latest}"

echo "Deploying TikTok API..."

# Navigate to deployment directory
cd /opt/tik-tok-api

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

    chmod +x /opt/tik-tok-api/deploy.sh
    log_success "Deployment script created at /opt/tik-tok-api/deploy.sh"
}

# Main setup function
main() {
    log_info "Starting server setup for TikTok API..."
    
    update_system
    install_docker
    install_docker_compose
    create_deployment_directory
    configure_firewall
    install_monitoring
    create_systemd_service
    create_deployment_script
    
    log_success "🎉 Server setup completed successfully!"
    log_info "Next steps:"
    log_info "1. Set up your environment variables (API_KEYS, MS_TOKENS, etc.)"
    log_info "2. Deploy using: ./scripts/deploy.sh"
    log_info "3. Monitor with: docker logs tik-tok-api-backend"
    log_info "4. Check health: curl http://localhost:8000/health"
}

# Run main function
main "$@"
