from django import forms
from login.models import Device, CustomUser
from .models import DeviceTransaction

class HandoverForm(forms.Form):
    device_serial_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter device serial number'
        })
    )
    employee_id = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter employee ID'
        })
    )
    device_condition = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # If initial device is provided, set its condition
        if 'initial' in kwargs and 'device_serial_number' in kwargs['initial']:
            try:
                device = Device.objects.get(serial_number=kwargs['initial']['device_serial_number'])
                self.fields['device_condition'].initial = device.condition
            except Device.DoesNotExist:
                pass

    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id')
        try:
            user = CustomUser.objects.get(employee_id=employee_id)
            if user.state == 'disable':
                raise forms.ValidationError("Cannot handover device to a disabled user.")
            
            # For limited admin, check if target user is in their department
            if self.user.admin_state == 'no' and user.department != self.user.department:
                raise forms.ValidationError("You can only hand over devices to users in your department.")
            
            # Check if user already has a device
            active_transaction = DeviceTransaction.objects.filter(
                user=user,
                device__state='assigned',
                status='completed'  # Only consider completed transactions
            ).first()
            
            if active_transaction:
                raise forms.ValidationError(f"User already has device {active_transaction.device.serial_number} assigned to them.")
                
            return employee_id
        except CustomUser.DoesNotExist:
            raise forms.ValidationError("Employee ID does not exist.")

    def clean_device_serial_number(self):
        serial_number = self.cleaned_data.get('device_serial_number')
        try:
            device = Device.objects.get(serial_number=serial_number)
            
            # Check if device is in stock
            if device.state != 'stock':
                raise forms.ValidationError("Device must be in stock for handover.")
            
            # For limited admin, check if device is in their department
            if self.user.admin_state == 'no' and device.department != self.user.department:
                raise forms.ValidationError("You can only hand over devices from your department.")
            
            # Set the device condition from the device
            self.cleaned_data['device_condition'] = device.condition
                
            return serial_number
        except Device.DoesNotExist:
            raise forms.ValidationError("Device serial number does not exist.")

    def clean_device_condition(self):
        condition = self.cleaned_data.get('device_condition')
        serial_number = self.cleaned_data.get('device_serial_number')
        
        try:
            device = Device.objects.get(serial_number=serial_number)
            # If device is damaged, condition must stay damaged unless user is admin
            if device.condition == 'damaged' and condition == 'working' and not self.user.admin_state == 'yes':
                raise forms.ValidationError("Only admin users can change device condition from damaged to working.")
            return condition
        except Device.DoesNotExist:
            return condition

class TakeoverForm(forms.Form):
    device_serial_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter device serial number'
        })
    )
    device_condition = forms.ChoiceField(
        choices=[('working', 'Working'), ('damaged', 'Damaged')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False  # Make it not required since it will be populated automatically
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # If initial device is provided, set its condition
        if 'initial' in kwargs and 'device_serial_number' in kwargs['initial']:
            try:
                device = Device.objects.get(serial_number=kwargs['initial']['device_serial_number'])
                self.fields['device_condition'].initial = device.condition
            except Device.DoesNotExist:
                pass

    def clean_device_serial_number(self):
        serial_number = self.cleaned_data.get('device_serial_number')
        try:
            device = Device.objects.get(serial_number=serial_number)
            
            # Check if device is assigned
            if device.state != 'assigned':
                raise forms.ValidationError("Device must be assigned to a user for takeover.")
            
            # For limited admin, check if device is in their department
            if self.user.admin_state == 'no' and device.department != self.user.department:
                raise forms.ValidationError("You can only take over devices from your department.")
            
            # For limited admin, check if the device is assigned to someone in their department
            if self.user.admin_state == 'no' and device.assigned_to and device.assigned_to.department != self.user.department:
                raise forms.ValidationError("You can only take over devices assigned to users in your department.")
            
            # Set the device condition from the device
            self.cleaned_data['device_condition'] = device.condition
                
            return serial_number
        except Device.DoesNotExist:
            raise forms.ValidationError("Device serial number does not exist.")

    def clean_device_condition(self):
        condition = self.cleaned_data.get('device_condition')
        serial_number = self.cleaned_data.get('device_serial_number')
        
        try:
            device = Device.objects.get(serial_number=serial_number)
            # If device is damaged, condition must stay damaged unless user is admin
            if device.condition == 'damaged' and condition == 'working' and not self.user.admin_state == 'yes':
                raise forms.ValidationError("Only admin users can change device condition from damaged to working.")
            return condition
        except Device.DoesNotExist:
            return condition 