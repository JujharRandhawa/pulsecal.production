# PulseCal SaaS Deployment Guide

This guide provides comprehensive instructions for deploying PulseCal as a professional SaaS application.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Local Development](#local-development)
4. [Production Deployment](#production-deployment)
5. [Docker Deployment](#docker-deployment)
6. [Cloud Deployment](#cloud-deployment)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Security Checklist](#security-checklist)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows 10/11
- **RAM**: Minimum 4GB, Recommended 8GB+
- **Storage**: 10GB+ free space
- **Network**: Stable internet connection

### Software Requirements
- **Docker**: 20.10+ and Docker Compose 2.0+
- **Python**: 3.11+ (for local development)
- **PostgreSQL**: 13+ (for local development)
- **Redis**: 6+ (for local development)

### Cloud Services (Production)
- **Database**: PostgreSQL (AWS RDS, Google Cloud SQL, or Azure Database)
- **Cache/Message Queue**: Redis (AWS ElastiCache, Google Cloud Memorystore)
- **Storage**: Object storage for media files (AWS S3, Google Cloud Storage)
- **Email**: SMTP service (SendGrid, Mailgun, AWS SES)
- **SMS**: Twilio account
- **Monitoring**: Sentry for error tracking

## Environment Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd pulsecal-system
```

### 2. Create Environment File
```bash
cp env_example.txt .env
```

### 3. Configure Environment Variables
Edit `.env` file with your specific values:

```env
# Environment Configuration
ENVIRONMENT=production
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Django Settings
SECRET_KEY=your-very-long-and-secure-secret-key-here
SITE_ID=1

# Database Settings
DB_NAME=pulsecal_production
DB_USER=pulsecal_user
DB_PASSWORD=your-secure-database-password
DB_HOST=your-database-host
DB_PORT=5432

# Redis Settings
REDIS_URL=redis://your-redis-host:6379/0

# Email Settings
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Google OAuth Settings
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/oauth2callback/

# Google Maps API Settings
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
GOOGLE_PLACES_API_KEY=your-google-places-api-key

# Security Settings
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# CORS Settings
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Sentry Configuration
SENTRY_DSN=your-sentry-dsn-here
```

## Local Development

### Option 1: Docker Development (Recommended)
```bash
# Start development environment
docker-compose up --build

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Run migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

### Option 2: Local Python Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up database
createdb pulsecal_dev
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## Production Deployment

### 1. Server Preparation

#### Ubuntu/Debian Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
```

#### SSL Certificate Setup
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 2. Application Deployment

#### Using Docker Compose
```bash
# Clone repository
git clone <repository-url>
cd pulsecal-system

# Create environment file
cp env_example.txt .env
# Edit .env with production values

# Deploy
./deploy.sh
```

#### Manual Deployment Steps
```bash
# Build and start services
docker-compose up --build -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Create logs directory
docker-compose exec web mkdir -p logs
```

### 3. Database Setup

#### PostgreSQL Configuration
```sql
-- Create database and user
CREATE DATABASE pulsecal_production;
CREATE USER pulsecal_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE pulsecal_production TO pulsecal_user;

-- Enable required extensions
\c pulsecal_production
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

#### Redis Configuration
```bash
# Install Redis
sudo apt install redis-server

# Configure Redis for production
sudo nano /etc/redis/redis.conf

# Key settings:
# bind 127.0.0.1
# requirepass your_redis_password
# maxmemory 256mb
# maxmemory-policy allkeys-lru

# Restart Redis
sudo systemctl restart redis
```

## Docker Deployment

### Production Docker Compose
```yaml
version: '3.8'

services:
  web:
    build: .
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - DEBUG=False
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      - db
      - redis

  celery:
    build: .
    command: celery -A pulsecal_system worker --loglevel=info
    restart: unless-stopped
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A pulsecal_system beat --loglevel=info
    restart: unless-stopped
    depends_on:
      - db
      - redis

volumes:
  static_volume:
  media_volume:
```

### Health Checks
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f web
docker-compose logs -f celery

# Health check endpoint
curl http://localhost/health/
```

## Cloud Deployment

### AWS Deployment

#### Using AWS ECS
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure

# Deploy to ECS
aws ecs create-cluster --cluster-name pulsecal-cluster
# ... additional ECS deployment steps
```

#### Using AWS EC2
```bash
# Launch EC2 instance
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --count 1 \
    --instance-type t3.medium \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxxxxx

# SSH into instance and follow server preparation steps
ssh -i your-key.pem ubuntu@your-instance-ip
```

### Google Cloud Deployment

#### Using Google Cloud Run
```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate
gcloud auth login

# Deploy to Cloud Run
gcloud run deploy pulsecal \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

### Azure Deployment

#### Using Azure Container Instances
```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login

# Deploy to Azure Container Instances
az container create \
    --resource-group pulsecal-rg \
    --name pulsecal-app \
    --image your-registry.azurecr.io/pulsecal:latest \
    --dns-name-label pulsecal-app \
    --ports 8000
```

## Monitoring & Maintenance

### Log Management
```bash
# View application logs
docker-compose logs -f web

# View Celery logs
docker-compose logs -f celery

# View database logs
docker-compose logs -f db

# Log rotation
sudo logrotate /etc/logrotate.d/pulsecal
```

### Backup Strategy
```bash
# Database backup
docker-compose exec db pg_dump -U pulsecal_user pulsecal_production > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T db pg_dump -U pulsecal_user pulsecal_production > $BACKUP_DIR/backup_$DATE.sql
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

### Performance Monitoring
```bash
# Monitor resource usage
docker stats

# Monitor application performance
curl -X GET http://localhost/api/health/

# Set up monitoring with Prometheus/Grafana
# ... monitoring setup instructions
```

## Security Checklist

### ✅ Environment Security
- [ ] Strong SECRET_KEY generated
- [ ] DEBUG=False in production
- [ ] ALLOWED_HOSTS properly configured
- [ ] HTTPS/SSL enabled
- [ ] Database password is secure
- [ ] Redis password configured

### ✅ Application Security
- [ ] Django security middleware enabled
- [ ] CSRF protection active
- [ ] XSS protection headers
- [ ] Content Security Policy configured
- [ ] Rate limiting implemented
- [ ] Input validation in place

### ✅ Infrastructure Security
- [ ] Firewall configured
- [ ] SSH key-based authentication
- [ ] Regular security updates
- [ ] Database access restricted
- [ ] Backup encryption enabled
- [ ] Monitoring and alerting

### ✅ Data Protection
- [ ] GDPR compliance measures
- [ ] Data encryption at rest
- [ ] Data encryption in transit
- [ ] Access logging enabled
- [ ] Audit trail implemented
- [ ] Data retention policies

## Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database connectivity
docker-compose exec web python manage.py dbshell

# Reset database
docker-compose down -v
docker-compose up -d db
docker-compose exec web python manage.py migrate
```

#### Static Files Not Loading
```bash
# Recollect static files
docker-compose exec web python manage.py collectstatic --noinput --clear

# Check static files directory
docker-compose exec web ls -la /app/staticfiles/
```

#### WebSocket Issues
```bash
# Check Redis connection
docker-compose exec redis redis-cli ping

# Restart WebSocket services
docker-compose restart web celery
```

#### Email Not Sending
```bash
# Test email configuration
docker-compose exec web python manage.py shell
# In shell: from django.core.mail import send_mail; send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])

# Check email logs
docker-compose logs web | grep -i mail
```

### Performance Issues

#### High Memory Usage
```bash
# Check memory usage
docker stats

# Optimize Django settings
# Add to settings.py:
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
    }
}
```

#### Slow Database Queries
```bash
# Enable query logging
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### Recovery Procedures

#### Application Recovery
```bash
# Restart all services
docker-compose restart

# Check service health
docker-compose ps

# View recent logs
docker-compose logs --tail=100
```

#### Database Recovery
```bash
# Restore from backup
docker-compose exec -T db psql -U pulsecal_user pulsecal_production < backup_file.sql

# Reset to clean state
docker-compose down -v
docker-compose up -d db
docker-compose exec web python manage.py migrate
```

## Support and Maintenance

### Regular Maintenance Tasks
- [ ] Weekly security updates
- [ ] Monthly backup verification
- [ ] Quarterly performance review
- [ ] Annual security audit

### Monitoring Alerts
- [ ] High CPU/Memory usage
- [ ] Database connection failures
- [ ] Email delivery failures
- [ ] SSL certificate expiration
- [ ] Disk space warnings

### Update Procedures
```bash
# Update application
git pull origin main
docker-compose build
docker-compose up -d

# Update dependencies
pip install -r requirements.txt --upgrade
docker-compose build --no-cache
```

For additional support, refer to the project documentation or contact the development team. 