import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoto.settings')
django.setup()

from login.models import CustomUser

def reset_users():
    try:
        # Remove all existing users
        CustomUser.objects.all().delete()
        print("All existing users have been removed.")
        
        # Create new admin user
        admin = CustomUser.objects.create_superuser(
            username='ADMIN001',
            password='admin@123',
            employee_id='ADMIN001',
            name='System Admin',
            department='IT',
            state='enable',
            admin_state='yes'
        )
        print("\nNew admin user created successfully:")
        print("Employee ID (username): ADMIN001")
        print("Password: admin@123")
        print("Department: IT")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    reset_users() 