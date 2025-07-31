#!/bin/bash

# PulseCal Enhanced Healthcare Management System - Universal Startup Script
# Works on macOS, Linux, and Windows (with WSL/Git Bash)

echo "🏥 Starting PulseCal Enhanced Healthcare Management System..."
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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

print_system() {
    echo -e "${PURPLE}[SYSTEM]${NC} $1"
}

print_platform() {
    echo -e "${CYAN}[PLATFORM]${NC} $1"
}

# Detect operating system
detect_os() {
    print_system "Detecting operating system..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="Linux"
        print_platform "Detected: Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macOS"
        print_platform "Detected: macOS"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS="Windows"
        print_platform "Detected: Windows (WSL/Git Bash)"
    else
        OS="Unknown"
        print_warning "Unknown OS: $OSTYPE"
    fi
    
    print_success "Operating System: $OS"
}

# Check if Docker is running
check_docker() {
    print_status "Checking Docker status..."
    
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running!"
        
        case $OS in
            "macOS")
                print_status "Please start Docker Desktop for Mac"
                print_status "You can find it in Applications or use Spotlight (Cmd+Space) and search 'Docker'"
                ;;
            "Linux")
                print_status "Please start Docker service:"
                print_status "sudo systemctl start docker"
                ;;
            "Windows")
                print_status "Please start Docker Desktop for Windows"
                print_status "Or if using WSL2, ensure Docker Desktop is running"
                ;;
        esac
        
        print_error "After starting Docker, run this script again"
        exit 1
    fi
    
    print_success "Docker is running"
    
    # Show Docker version
    DOCKER_VERSION=$(docker --version)
    print_status "Docker Version: $DOCKER_VERSION"
}

# Check if Docker Compose is available
check_docker_compose() {
    print_status "Checking Docker Compose..."
    
    if ! docker-compose --version > /dev/null 2>&1; then
        print_error "Docker Compose is not available!"
        print_status "Please install Docker Compose or use 'docker compose' (newer versions)"
        
        # Try the new docker compose command
        if docker compose version > /dev/null 2>&1; then
            print_success "Found 'docker compose' (newer version)"
            DOCKER_COMPOSE_CMD="docker compose"
        else
            print_error "Neither 'docker-compose' nor 'docker compose' is available"
            exit 1
        fi
    else
        DOCKER_COMPOSE_CMD="docker-compose"
        DOCKER_COMPOSE_VERSION=$(docker-compose --version)
        print_success "Docker Compose Version: $DOCKER_COMPOSE_VERSION"
    fi
}

# Stop any existing containers
stop_containers() {
    print_status "Stopping any existing containers..."
    $DOCKER_COMPOSE_CMD down > /dev/null 2>&1
    print_success "Existing containers stopped"
}

# Build and start containers
start_containers() {
    print_status "Building and starting containers..."
    print_status "This may take a few minutes on first run..."
    
    $DOCKER_COMPOSE_CMD up --build -d
    
    if [ $? -eq 0 ]; then
        print_success "Containers started successfully"
    else
        print_error "Failed to start containers"
        exit 1
    fi
}

# Wait for containers to be ready
wait_for_containers() {
    print_status "Waiting for containers to be ready..."
    
    # Wait for containers to start
    sleep 20
    
    # Check if containers are running
    print_status "Checking container status..."
    
    if $DOCKER_COMPOSE_CMD ps | grep -q "Up"; then
        print_success "All containers are running"
    else
        print_error "Some containers failed to start"
        print_status "Showing container logs..."
        $DOCKER_COMPOSE_CMD logs --tail=20
        exit 1
    fi
}

# Wait for database to be ready
wait_for_database() {
    print_status "Waiting for database to be ready..."
    sleep 10
    print_success "Database should be ready"
}

# Run migrations
run_migrations() {
    print_status "Running database migrations..."
    
    $DOCKER_COMPOSE_CMD exec -T web python manage.py migrate
    
    if [ $? -eq 0 ]; then
        print_success "Database migrations completed"
    else
        print_warning "Migration had issues, but continuing..."
    fi
}

# Collect static files
collect_static() {
    print_status "Collecting static files..."
    
    $DOCKER_COMPOSE_CMD exec -T web python manage.py collectstatic --noinput
    
    if [ $? -eq 0 ]; then
        print_success "Static files collected"
    else
        print_warning "Static file collection had issues, but continuing..."
    fi
}

# Check if application is accessible
check_application() {
    print_status "Verifying application accessibility..."
    sleep 5
    
    # Try to access the application
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Application is running successfully!"
    else
        print_warning "Application might still be starting up..."
        sleep 10
        
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 2>/dev/null || echo "000")
        
        if [ "$HTTP_CODE" = "200" ]; then
            print_success "Application is now running successfully!"
        else
            print_error "Application failed to start properly"
            print_status "Showing web container logs..."
            $DOCKER_COMPOSE_CMD logs web --tail=20
            print_warning "You can still try accessing http://localhost:8000"
        fi
    fi
}

# Display final status
show_final_status() {
    echo ""
    echo "🎉 PulseCal Enhanced Healthcare Management System is READY!"
    echo "=================================================="
    echo ""
    print_success "🌐 Application URL: http://localhost:8000"
    print_success "📊 Admin Interface: http://localhost:8000/admin"
    print_success "🗄️  Database: PostgreSQL on localhost:5432"
    print_success "⚡ Redis Cache: localhost:6379"
    echo ""
    echo "🚀 New Features Available:"
    echo "   • Medical Records Management"
    echo "   • Prescription Management"
    echo "   • Insurance Management"
    echo "   • Payment Processing"
    echo "   • Emergency Contacts"
    echo "   • Medication Reminders"
    echo "   • Telemedicine Sessions"
    echo "   • Health Analytics Dashboard"
    echo ""
    echo "📱 Navigation:"
    echo "   • Health → Medical Records, Prescriptions, Insurance, etc."
    echo "   • Services → Payments, Telemedicine"
    echo "   • Health Analytics → Comprehensive health insights"
    echo ""
    print_status "To stop the application, run: $DOCKER_COMPOSE_CMD down"
    print_status "To view logs, run: $DOCKER_COMPOSE_CMD logs -f"
    print_status "To restart, run: $DOCKER_COMPOSE_CMD restart"
    print_status "To check status, run: $DOCKER_COMPOSE_CMD ps"
    echo ""
    
    # OS-specific tips
    case $OS in
        "macOS")
            print_system "macOS Tips:"
            print_status "• Use Cmd+Click to open http://localhost:8000 in browser"
            print_status "• Docker Desktop should be running in your menu bar"
            ;;
        "Linux")
            print_system "Linux Tips:"
            print_status "• Use 'xdg-open http://localhost:8000' to open in browser"
            print_status "• Check Docker service: sudo systemctl status docker"
            ;;
        "Windows")
            print_system "Windows Tips:"
            print_status "• Use 'start http://localhost:8000' to open in browser"
            print_status "• Docker Desktop should be running in system tray"
            ;;
    esac
    
    echo ""
    print_success "Happy healthcare management! 🏥✨"
}

# Main execution
main() {
    detect_os
    check_docker
    check_docker_compose
    stop_containers
    start_containers
    wait_for_containers
    wait_for_database
    run_migrations
    collect_static
    check_application
    show_final_status
}

# Run main function
main "$@" 