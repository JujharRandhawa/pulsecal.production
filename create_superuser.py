import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulsecal_system.settings')
django.setup()

from django.contrib.auth.models import User

def create_superuser():
    # Check if superuser already exists
    if User.objects.filter(is_superuser=True).exists():
        print("Superuser already exists!")
        return
    
    # Create superuser
    try:
        superuser = User.objects.create_superuser(
            username='superadmin',
            email='admin@pulsecal.com',
            password='superadmin123',
            first_name='Super',
            last_name='Administrator'
        )
        print("✅ Superuser created successfully!")
        print(f"Username: {superuser.username}")
        print(f"Email: {superuser.email}")
        print(f"Password: superadmin123")
        print("\nYou can now login at: http://localhost:8000/admin/")
        
    except Exception as e:
        print(f"❌ Error creating superuser: {e}")

if __name__ == "__main__":
    create_superuser() 