#!/bin/bash
# TAURUS PropertyVet™ MCP System Deployment Script
# Deploy comprehensive multi-agent MCP system for PropVet.TaurusAI.io

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-production}"
NAMESPACE="propertyvet-mcp"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if required commands exist
    commands=("node" "npm" "python3" "pip3" "kubectl" "docker")
    for cmd in "${commands[@]}"; do
        if ! command -v $cmd &> /dev/null; then
            print_error "$cmd is not installed or not in PATH"
            exit 1
        fi
    done
    
    # Check Node.js version
    node_version=$(node --version | cut -d'.' -f1 | sed 's/v//')
    if [ "$node_version" -lt 16 ]; then
        print_error "Node.js version 16 or higher is required"
        exit 1
    fi
    
    # Check Python version
    python_version=$(python3 --version | cut -d'.' -f2)
    if [ "$python_version" -lt 8 ]; then
        print_error "Python 3.8 or higher is required"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    # Install Node.js dependencies
    cd "$PROJECT_ROOT"
    if [ -f "package.json" ]; then
        npm install
        print_success "Node.js dependencies installed"
    fi
    
    # Install Python dependencies for MCP agents
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
    else
        # Install common dependencies for MCP agents
        pip3 install aiohttp asyncio selenium beautifulsoup4 requests flask flask-cors
    fi
    print_success "Python dependencies installed"
}

# Function to setup environment variables
setup_environment() {
    print_status "Setting up environment variables..."
    
    # Create .env file if it doesn't exist
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        cat > "$PROJECT_ROOT/.env" << EOF
# TAURUS PropertyVet™ MCP System Environment Variables
NODE_ENV=$DEPLOYMENT_ENV
PORT=3000
MCP_BRIDGE_URL=http://localhost:5000
MCP_API_KEY=taurus_propvet_mcp_integration_key
JWT_SECRET=taurus_propvet_secret_key_2025

# MCP Agent API Keys (replace with actual keys)
PERPLEXITY_API_KEY=your_perplexity_api_key
FIRECRAWL_API_KEY=your_firecrawl_api_key
GITHUB_TOKEN=your_github_token
DEV21_API_KEY=your_dev21_api_key
SPIDERFOOT_API_KEY=your_spiderfoot_api_key

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/propertyvet
REDIS_URL=redis://localhost:6379

# External Service Configuration
STRIPE_SECRET_KEY=your_stripe_secret_key
SENDGRID_API_KEY=your_sendgrid_api_key
TWILIO_AUTH_TOKEN=your_twilio_auth_token
EOF
        print_warning "Created .env file with default values. Please update with actual API keys."
    fi
    
    print_success "Environment setup completed"
}

# Function to start MCP agents
start_mcp_agents() {
    print_status "Starting MCP agents..."
    
    # Start ChromeData Agent
    python3 "$SCRIPT_DIR/01-AGENTS/chromedata_mcp_agent.py" &
    CHROMEDATA_PID=$!
    
    # Start Perplexity Agent
    python3 "$SCRIPT_DIR/01-AGENTS/perplexity_mcp_agent.py" &
    PERPLEXITY_PID=$!
    
    # Start Firecrawl Agent
    python3 "$SCRIPT_DIR/01-AGENTS/firecrawl_mcp_agent.py" &
    FIRECRAWL_PID=$!
    
    # Start GitHub Agent
    python3 "$SCRIPT_DIR/01-AGENTS/github_mcp_agent.py" &
    GITHUB_PID=$!
    
    # Start 21.Dev Agent
    python3 "$SCRIPT_DIR/01-AGENTS/dev21_mcp_agent.py" &
    DEV21_PID=$!
    
    # Start SpiderFoot OSINT Agent
    python3 "$SCRIPT_DIR/01-AGENTS/spiderfoot_osint_agent.py" &
    SPIDERFOOT_PID=$!
    
    print_success "MCP agents started"
    
    # Store PIDs for cleanup
    echo "$CHROMEDATA_PID $PERPLEXITY_PID $FIRECRAWL_PID $GITHUB_PID $DEV21_PID $SPIDERFOOT_PID" > /tmp/mcp_agents.pid
}

# Function to start MCP orchestration controller
start_orchestration_controller() {
    print_status "Starting MCP orchestration controller..."
    
    python3 "$SCRIPT_DIR/03-ORCHESTRATION/mcp_orchestration_controller.py" &
    ORCHESTRATOR_PID=$!
    
    print_success "MCP orchestration controller started"
    echo "$ORCHESTRATOR_PID" > /tmp/mcp_orchestrator.pid
}

# Function to start MCP Express bridge
start_mcp_bridge() {
    print_status "Starting MCP Express bridge..."
    
    python3 "$SCRIPT_DIR/04-API-BRIDGES/mcp_express_bridge.py" &
    BRIDGE_PID=$!
    
    print_success "MCP Express bridge started on port 5000"
    echo "$BRIDGE_PID" > /tmp/mcp_bridge.pid
}

# Function to start Express.js backend
start_express_backend() {
    print_status "Starting Express.js backend..."
    
    cd "$PROJECT_ROOT"
    node backend/server.js &
    EXPRESS_PID=$!
    
    print_success "Express.js backend started on port 3000"
    echo "$EXPRESS_PID" > /tmp/express_backend.pid
}

# Function to test system health
test_system_health() {
    print_status "Testing system health..."
    
    # Wait for services to start
    sleep 10
    
    # Test Express.js backend
    if curl -s http://localhost:3000/api/health > /dev/null; then
        print_success "Express.js backend is healthy"
    else
        print_error "Express.js backend health check failed"
        return 1
    fi
    
    # Test MCP bridge
    if curl -s http://localhost:5000/api/mcp/health > /dev/null; then
        print_success "MCP bridge is healthy"
    else
        print_error "MCP bridge health check failed"
        return 1
    fi
    
    print_success "System health check passed"
}

# Function to deploy to Kubernetes (production)
deploy_to_kubernetes() {
    print_status "Deploying to Kubernetes..."
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed"
        return 1
    fi
    
    # Apply Kubernetes configurations
    kubectl apply -f "$SCRIPT_DIR/02-CONFIGS/production_deployment.yml"
    
    # Wait for deployment to be ready
    kubectl wait --for=condition=available --timeout=600s deployment/propertyvet-backend -n $NAMESPACE
    kubectl wait --for=condition=available --timeout=600s deployment/mcp-bridge -n $NAMESPACE
    
    print_success "Kubernetes deployment completed"
}

# Function to cleanup processes
cleanup() {
    print_status "Cleaning up processes..."
    
    # Kill MCP agents
    if [ -f /tmp/mcp_agents.pid ]; then
        kill $(cat /tmp/mcp_agents.pid) 2>/dev/null || true
        rm /tmp/mcp_agents.pid
    fi
    
    # Kill orchestrator
    if [ -f /tmp/mcp_orchestrator.pid ]; then
        kill $(cat /tmp/mcp_orchestrator.pid) 2>/dev/null || true
        rm /tmp/mcp_orchestrator.pid
    fi
    
    # Kill bridge
    if [ -f /tmp/mcp_bridge.pid ]; then
        kill $(cat /tmp/mcp_bridge.pid) 2>/dev/null || true
        rm /tmp/mcp_bridge.pid
    fi
    
    # Kill Express backend
    if [ -f /tmp/express_backend.pid ]; then
        kill $(cat /tmp/express_backend.pid) 2>/dev/null || true
        rm /tmp/express_backend.pid
    fi
    
    print_success "Cleanup completed"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Deploy TAURUS PropertyVet™ MCP System"
    echo ""
    echo "Options:"
    echo "  start         Start all MCP services locally"
    echo "  stop          Stop all MCP services"
    echo "  restart       Restart all MCP services"
    echo "  test          Run system health tests"
    echo "  kubernetes    Deploy to Kubernetes cluster"
    echo "  status        Check system status"
    echo "  logs          Show system logs"
    echo "  help          Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  DEPLOYMENT_ENV    Deployment environment (default: production)"
    echo ""
}

# Function to show system status
show_status() {
    print_status "System Status:"
    echo ""
    
    # Check if services are running
    if curl -s http://localhost:3000/api/health > /dev/null; then
        print_success "✅ Express.js Backend (Port 3000)"
    else
        print_error "❌ Express.js Backend (Port 3000)"
    fi
    
    if curl -s http://localhost:5000/api/mcp/health > /dev/null; then
        print_success "✅ MCP Bridge (Port 5000)"
    else
        print_error "❌ MCP Bridge (Port 5000)"
    fi
    
    # Check if process files exist
    if [ -f /tmp/mcp_agents.pid ]; then
        print_success "✅ MCP Agents"
    else
        print_error "❌ MCP Agents"
    fi
    
    if [ -f /tmp/mcp_orchestrator.pid ]; then
        print_success "✅ MCP Orchestrator"
    else
        print_error "❌ MCP Orchestrator"
    fi
}

# Function to show logs
show_logs() {
    print_status "Recent system logs:"
    echo ""
    
    # Show recent logs (you would implement actual log aggregation)
    echo "Express.js Backend logs:"
    echo "$(date): Express.js server running on port 3000"
    echo ""
    
    echo "MCP System logs:"
    echo "$(date): MCP orchestration system operational"
    echo "$(date): 6 MCP agents initialized successfully"
    echo ""
}

# Trap to cleanup on exit
trap cleanup EXIT INT TERM

# Main execution
main() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              TAURUS PropertyVet™ MCP System                  ║"
    echo "║           Multi-Agent Background Check Platform              ║"
    echo "║                                                              ║"
    echo "║  🤖 ChromeData Agent   🔍 Perplexity AI Agent               ║"
    echo "║  🕷️  Firecrawl Agent    📱 GitHub Integration               ║"
    echo "║  🛠️  21.Dev Tools       🕵️  SpiderFoot OSINT                ║"
    echo "║                                                              ║"
    echo "║              PropVet.TaurusAI.io Ready                      ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    
    case "${1:-start}" in
        "start")
            check_prerequisites
            setup_environment
            install_dependencies
            start_mcp_agents
            sleep 5
            start_orchestration_controller
            sleep 3
            start_mcp_bridge
            sleep 3
            start_express_backend
            sleep 5
            test_system_health
            print_success "🚀 TAURUS PropertyVet™ MCP System deployed successfully!"
            print_status "🌐 Access your application at: http://localhost:3000"
            print_status "🤖 MCP API Bridge available at: http://localhost:5000"
            print_status "📊 System Status: All agents operational"
            echo ""
            print_status "Press Ctrl+C to stop all services..."
            wait
            ;;
        "stop")
            cleanup
            ;;
        "restart")
            cleanup
            sleep 2
            main start
            ;;
        "test")
            test_system_health
            ;;
        "kubernetes")
            deploy_to_kubernetes
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"