from django.core.management.base import BaseCommand
from login.models import CustomUser

class Command(BaseCommand):
    help = 'Creates a superuser with all required fields'

    def handle(self, *args, **options):
        if not CustomUser.objects.filter(username='admin').exists():
            CustomUser.objects.create_superuser(
                username='admin',
                password='admin@12345',
                email='admin@example.com',
                name='System Admin',
                employee_id='ADMIN002',
                department='IT',
                admin_state='yes',
                state='enable'
            )
            self.stdout.write(self.style.SUCCESS('Superuser created successfully')) 