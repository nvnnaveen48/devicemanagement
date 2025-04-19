from django.db import models
from django.utils import timezone
from login.models import CustomUser, Device

# Create your models here.

class DeviceTransaction(models.Model):
    DEVICE_STATUS_CHOICES = [
        ('stock', 'Stock'),
        ('assigned', 'Assigned'),
        ('damaged', 'Damaged'),
        ('maintenance', 'Maintenance')
    ]
    
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]

    # Device information
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    device_serial_number = models.CharField(max_length=50, unique=True)  # Redundant but useful for quick lookups
    
    # User information
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='device_transaction_assignments')
    user_name = models.CharField(max_length=255)  # Redundant but useful for quick lookups
    
    # Handover information
    handover_datetime = models.DateTimeField(null=True, blank=True)
    handover_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='device_handovers_given')
    
    # Takeover information
    takeover_datetime = models.DateTimeField(null=True, blank=True)
    takeover_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='device_takeovers_received')
    
    # Status information
    device_status = models.CharField(max_length=20, choices=DEVICE_STATUS_CHOICES)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='pending')
    
    # Additional information
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_device_transaction_records')
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='updated_device_transactions')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Device Transaction'
        verbose_name_plural = 'Device Transactions'

    def __str__(self):
        return f"{self.device.serial_number} - {self.status} ({self.created_at})"

    def save(self, *args, **kwargs):
        # Ensure device serial number exists in inventory
        if not Device.objects.filter(serial_number=self.device_serial_number).exists():
            raise ValueError("Device serial number must exist in inventory")
        
        # Ensure user is not an admin (admin_state is 'normal')
        if self.user.admin_state != '-':
            raise ValueError("Only normal users can be assigned devices")
        
        # Update redundant fields
        self.user_name = self.user.name
        
        # Update timestamps based on status changes
        if self.status == 'completed' and not self.takeover_datetime:
            self.takeover_datetime = timezone.now()
        
        super().save(*args, **kwargs)
