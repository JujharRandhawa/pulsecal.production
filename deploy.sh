#!/bin/bash

# PulseCal Deployment Script
# This script automates the deployment of the PulseCal SaaS application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found. Please create one from env_example.txt"
    exit 1
fi

# Load environment variables
source .env

print_status "Starting PulseCal deployment..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose are available"

# Stop existing containers if running
print_status "Stopping existing containers..."
docker-compose down --remove-orphans

# Build and start services
print_status "Building and starting services..."
docker-compose up --build -d

# Wait for services to be healthy
print_status "Waiting for services to be healthy..."
sleep 30

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    print_error "Services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

print_status "Services are running"

# Run database migrations
print_status "Running database migrations..."
docker-compose exec web python manage.py migrate

# Create superuser if it doesn't exist
print_status "Checking for superuser..."
if ! docker-compose exec web python manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.filter(is_superuser=True).exists())" | grep -q "True"; then
    print_warning "No superuser found. You can create one with:"
    echo "docker-compose exec web python manage.py createsuperuser"
fi

# Collect static files
print_status "Collecting static files..."
docker-compose exec web python manage.py collectstatic --noinput

# Create logs directory
print_status "Creating logs directory..."
docker-compose exec web mkdir -p logs

print_status "Deployment completed successfully!"
echo ""
print_status "Application is available at: http://localhost"
print_status "Admin interface: http://localhost/admin"
echo ""
print_status "Useful commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop services: docker-compose down"
echo "  Restart services: docker-compose restart"
echo "  Create superuser: docker-compose exec web python manage.py createsuperuser"
echo "  Run management commands: docker-compose exec web python manage.py [command]" 