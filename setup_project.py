#!/usr/bin/env python3
"""
PulseCal Project Setup Script
This script sets up the PulseCal Django project on any machine.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python {version.major}.{version.minor} is not supported. Please install Python 3.8+")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    
    # Upgrade pip first
    if not run_command("python -m pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing requirements"):
        return False
    
    return True

def setup_database():
    """Set up the database"""
    print("🗄️ Setting up database...")
    
    # Create migrations
    if not run_command("python manage.py makemigrations", "Creating migrations"):
        return False
    
    # Apply migrations
    if not run_command("python manage.py migrate", "Applying migrations"):
        return False
    
    return True

def create_superuser():
    """Create a superuser if none exists"""
    print("👤 Checking for superuser...")
    
    # Check if superuser exists
    try:
        result = subprocess.run(
            "python manage.py shell -c \"from django.contrib.auth.models import User; print(User.objects.filter(is_superuser=True).count())\"",
            shell=True, capture_output=True, text=True
        )
        superuser_count = int(result.stdout.strip())
        
        if superuser_count == 0:
            print("🔧 No superuser found. Creating one...")
            print("Please enter the following details for the superuser:")
            
            # Create superuser interactively
            if not run_command("python manage.py createsuperuser", "Creating superuser"):
                print("⚠️ Superuser creation failed. You can create one later with: python manage.py createsuperuser")
        else:
            print(f"✅ Found {superuser_count} superuser(s)")
    except:
        print("⚠️ Could not check for superuser. You can create one later with: python manage.py createsuperuser")

def create_sample_data():
    """Create sample data for testing"""
    print("📊 Creating sample data...")
    
    if not run_command("python manage.py create_sample_data", "Creating sample data"):
        print("⚠️ Sample data creation failed. This is optional.")
    
    return True

def setup_static_files():
    """Set up static files"""
    print("📁 Setting up static files...")
    
    if not run_command("python manage.py collectstatic --noinput", "Collecting static files"):
        print("⚠️ Static file collection failed. This is optional.")
    
    return True

def create_directories():
    """Create necessary directories"""
    print("📂 Creating necessary directories...")
    
    directories = ['logs', 'media', 'staticfiles']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    return True

def run_checks():
    """Run Django system checks"""
    print("🔍 Running system checks...")
    
    if not run_command("python manage.py check", "Running Django checks"):
        return False
    
    return True

def main():
    """Main setup function"""
    print("🚀 PulseCal Project Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create necessary directories
    if not create_directories():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies. Please check your internet connection and try again.")
        sys.exit(1)
    
    # Run Django checks
    if not run_checks():
        print("❌ Django system checks failed. Please fix the issues and try again.")
        sys.exit(1)
    
    # Setup database
    if not setup_database():
        print("❌ Database setup failed. Please check your database configuration.")
        sys.exit(1)
    
    # Create superuser
    create_superuser()
    
    # Create sample data
    create_sample_data()
    
    # Setup static files
    setup_static_files()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\nTo start the server, run one of the following:")
    print("  • Windows: double-click 'start_server.bat'")
    print("  • PowerShell: .\\start_server.ps1")
    print("  • Command line: python manage.py runserver")
    print("\nThe server will be available at: http://127.0.0.1:8000/")
    print("=" * 50)

if __name__ == "__main__":
    main() 