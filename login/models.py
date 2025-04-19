from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.utils import timezone

class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('employee_id', 'ADMIN001')
        extra_fields.setdefault('name', 'System Admin')
        extra_fields.setdefault('state', 'enable')
        extra_fields.setdefault('admin_state', 'yes')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)

class CustomUser(AbstractUser):
    name = models.CharField(max_length=255)
    employee_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=10, choices=[('enable', 'Enable'), ('disable', 'Disable')], default='enable')
    create_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='created_users')
    create_datetime = models.DateTimeField(auto_now_add=True)
    enable_by = models.CharField(max_length=50, null=True, blank=True)
    enable_datetime = models.DateTimeField(null=True, blank=True)
    disable_by = models.CharField(max_length=50, null=True, blank=True)
    disable_datetime = models.DateTimeField(null=True, blank=True)
    admin_state = models.CharField(
        max_length=3, 
        choices=[('yes', 'Yes'), ('no', 'No'), ('-', 'Normal')], 
        default='-'
    )

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if self.state == 'enable' and not self.enable_datetime:
            self.enable_datetime = timezone.now()
            self.disable_datetime = None
            self.disable_by = None
        elif self.state == 'disable' and not self.disable_datetime:
            self.disable_datetime = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'users'

class Device(models.Model):
    DEVICE_CONDITIONS = [
        ('working', 'Working'),
        ('damaged', 'Damaged')
    ]
    
    DEVICE_STATES = [
        ('stock', 'Stock'),
        ('assigned', 'Assigned'),
        ('maintenance', 'Maintenance')
    ]

    MANUFACTURER_CHOICES = [
        ('Zebra', 'Zebra'),
        ('Honeywell', 'Honeywell'),
        ('Datalogic', 'Datalogic'),
        ('Samsung', 'Samsung'),
        ('Urovo', 'Urovo'),
        ('A4Tech', 'A4Tech'),
        ('Acer', 'Acer'),
        ('Other', 'Other')
    ]
    
    serial_number = models.CharField(max_length=100, unique=True)
    make = models.CharField(max_length=100, help_text="Enter the manufacturer/brand of the device")
    model = models.CharField(max_length=100, help_text="Enter the model name/number of the device")
    condition = models.CharField(max_length=20, choices=DEVICE_CONDITIONS, default='working')
    state = models.CharField(max_length=20, choices=DEVICE_STATES, default='stock')
    department = models.CharField(max_length=100)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_devices')
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='updated_devices')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='devices_assigned')

    def __str__(self):
        return f"{self.make} {self.model} ({self.serial_number})"

class HandoverTakeover(models.Model):
    TRANSACTION_TYPES = [
        ('handover', 'Handover'),
        ('takeover', 'Takeover')
    ]
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    from_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='handovers_given')
    to_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='handovers_received')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    device_condition = models.CharField(max_length=20, choices=Device.DEVICE_CONDITIONS, default='working')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_handover_transactions')
    transaction_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.device.serial_number} ({self.transaction_date})"
