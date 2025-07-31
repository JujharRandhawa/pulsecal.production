import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulsecal_system.settings')
django.setup()

from django.db import connection

def inspect_organization_table():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'appointments_organization'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        print("Organization table columns:")
        print("Column Name | Data Type | Nullable | Default")
        print("-" * 50)
        for col in columns:
            print(f"{col[0]:<12} | {col[1]:<10} | {col[2]:<8} | {col[3] or 'NULL'}")

if __name__ == "__main__":
    inspect_organization_table() 