#!/usr/bin/env python3
"""
Test script to verify PulseCal setup
"""

import os
import sys
import django
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        import django
        print(f"✅ Django {django.get_version()}")
    except ImportError as e:
        print(f"❌ Django import failed: {e}")
        return False
    
    try:
        import reportlab
        print("✅ ReportLab")
    except ImportError as e:
        print(f"❌ ReportLab import failed: {e}")
        return False
    
    try:
        import pandas
        print("✅ Pandas")
    except ImportError as e:
        print(f"❌ Pandas import failed: {e}")
        return False
    
    try:
        import openpyxl
        print("✅ OpenPyXL")
    except ImportError as e:
        print(f"❌ OpenPyXL import failed: {e}")
        return False
    
    try:
        import channels
        print("✅ Django Channels")
    except ImportError as e:
        print(f"❌ Django Channels import failed: {e}")
        return False
    
    return True

def test_django_setup():
    """Test Django setup"""
    print("\n🔍 Testing Django setup...")
    
    # Add project to Python path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulsecal_system.settings')
    
    try:
        django.setup()
        print("✅ Django setup successful")
    except Exception as e:
        print(f"❌ Django setup failed: {e}")
        return False
    
    return True

def test_models():
    """Test model imports"""
    print("\n🔍 Testing models...")
    
    try:
        from appointments.models import Appointment, UserProfile, Organization
        print("✅ Models imported successfully")
    except Exception as e:
        print(f"❌ Model import failed: {e}")
        return False
    
    return True

def test_database():
    """Test database connection"""
    print("\n🔍 Testing database...")
    
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("🧪 PulseCal Setup Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_django_setup,
        test_models,
        test_database,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print(f"❌ Test failed: {test.__name__}")
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Setup is working correctly.")
        print("\nTo start the server, run:")
        print("  python manage.py runserver")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 