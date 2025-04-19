from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import CustomUser, Device, HandoverTakeover
from dashboard.models import DeviceTransaction
from dashboard.forms import HandoverForm, TakeoverForm
import csv
import io
from django.http import JsonResponse, HttpResponse
from datetime import datetime
import json

def login(request):
    # Redirect to dashboard if user is already authenticated
    if request.user.is_authenticated:
        return redirect('login:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.state == 'enable':
                auth_login(request, user)
                # Set session expiry
                if not request.POST.get('remember_me', None):
                    request.session.set_expiry(0)  # Session expires when browser closes
                # Get next URL from query parameters or use default
                next_url = request.GET.get('next', 'login:dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Your account is disabled.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login/login.html')

@login_required
def dashboard(request):
    if request.user.state != 'enable':
        logout(request)
        return redirect('login:login')

    # Get devices based on user's admin state
    if request.user.admin_state == 'yes':
        devices = Device.objects.all()
        users = CustomUser.objects.all()
    else:
        devices = Device.objects.filter(department=request.user.department)
        users = CustomUser.objects.filter(department=request.user.department)

    # Calculate device statistics
    total_devices = devices.count()
    damaged_devices = devices.filter(condition='damaged').count()
    available_devices = devices.filter(state='stock').count()
    assigned_devices = devices.filter(state='assigned').count()
    maintenance_devices = devices.filter(state='maintenance').count()

    # Calculate user statistics
    total_users = users.count()
    admin_users = users.filter(admin_state='yes').count()
    limited_admin_users = users.filter(admin_state='no').count()
    normal_users = users.filter(admin_state='-').count()
    enabled_users = users.filter(state='enable').count()
    disabled_users = users.filter(state='disable').count()

    # Calculate department-wise statistics
    departments = {}
    for dept in devices.values_list('department', flat=True).distinct():
        dept_devices = devices.filter(department=dept)
        dept_users = users.filter(department=dept)
        departments[dept] = {
            'total': dept_devices.count(),
            'damaged': dept_devices.filter(condition='damaged').count(),
            'available': dept_devices.filter(state='stock').count(),
            'assigned': dept_devices.filter(state='assigned').count(),
            'maintenance': dept_devices.filter(state='maintenance').count(),
            'users': {
                'total': dept_users.count(),
                'admin': dept_users.filter(admin_state='yes').count(),
                'limited_admin': dept_users.filter(admin_state='no').count(),
                'normal': dept_users.filter(admin_state='-').count(),
                'enabled': dept_users.filter(state='enable').count(),
                'disabled': dept_users.filter(state='disable').count(),
            }
        }

    # Get recent transactions
    recent_transactions = HandoverTakeover.objects.all().order_by('-transaction_date')[:5]

    context = {
        'total_devices': total_devices,
        'damaged_devices': damaged_devices,
        'available_devices': available_devices,
        'assigned_devices': assigned_devices,
        'maintenance_devices': maintenance_devices,
        'total_users': total_users,
        'admin_users': admin_users,
        'limited_admin_users': limited_admin_users,
        'normal_users': normal_users,
        'enabled_users': enabled_users,
        'disabled_users': disabled_users,
        'departments': departments,
        'recent_transactions': recent_transactions,
    }

    return render(request, 'login/dashboard.html', context)

# User Management Views
@login_required
def user_list(request):
    # Get filter parameters
    state = request.GET.get('state')
    admin_state = request.GET.get('admin_state')
    
    # Base queryset based on user's admin state
    if request.user.admin_state == 'yes':
        users = CustomUser.objects.all()
    else:
        # Limited admin can only see normal users in their department
        users = CustomUser.objects.filter(department=request.user.department, admin_state='-')
    
    # Apply filters
    if state:
        users = users.filter(state=state)
    if admin_state:
        users = users.filter(admin_state=admin_state)
    
    # Order by username
    users = users.order_by('username')
    
    context = {
        'users': users,
        'current_state': state,
        'current_admin_state': admin_state
    }
    return render(request, 'login/user_list.html', context)

@login_required
def user_add(request):
    # Check if user has admin_state='no', they can only add normal users
    if request.user.admin_state == 'no':
        if request.method == 'POST':
            # Force admin_state to '-' for limited admins
            request.POST = request.POST.copy()
            request.POST['admin_state'] = '-'
    
    context = {
        'edit_user': None,
        'form_data': request.POST if request.method == 'POST' else {},
    }
    
    if request.method == 'POST':
        try:
            employee_id = request.POST.get('employee_id')
            name = request.POST.get('name')
            admin_state = request.POST.get('admin_state', '-')
            
            # Validate required fields
            required_fields = [employee_id, name]
            
            if not all(required_fields):
                messages.error(request, 'All required fields must be filled.')
                return render(request, 'login/user_form.html', context)

            # Enhanced employee_id validation
            if not employee_id.strip():
                messages.error(request, 'Employee ID cannot be empty.')
                return render(request, 'login/user_form.html', context)

            # Check if employee_id already exists (case-insensitive)
            if CustomUser.objects.filter(employee_id__iexact=employee_id).exists():
                messages.error(request, f'Employee ID "{employee_id}" is already in use. Please use a different Employee ID.')
                return render(request, 'login/user_form.html', context)
            
            # Handle password validation
            password = None
            confirm_password = None
            
            if request.user.admin_state == 'yes':
                if admin_state in ['yes', 'no']:  # Admin or Limited Admin
                    # Password required for admin and limited admin users
                    password = request.POST.get('password')
                    confirm_password = request.POST.get('confirm_password')
                    required_fields.extend([password, confirm_password])
                else:  # Normal user
                    # Generate default password for normal users
                    password = f"Welcome@{employee_id}"
            else:
                # Limited admin creating normal user
                password = f"Welcome@{employee_id}"
            
            # Validate password match for admin creating admin/limited admin users
            if request.user.admin_state == 'yes' and admin_state in ['yes', 'no']:
                if not password or not confirm_password:
                    messages.error(request, 'Password and confirmation are required for admin users.')
                    return render(request, 'login/user_form.html', context)
                if password != confirm_password:
                    messages.error(request, 'Passwords do not match.')
                    return render(request, 'login/user_form.html', context)
            
            # Handle department based on admin state
            if request.user.admin_state == 'yes':
                department = request.POST.get('department')
                if not department:
                    messages.error(request, 'Department is required.')
                    return render(request, 'login/user_form.html', context)
            else:
                department = request.user.department  # Limited admin's department
            
            # Create the user
            user = CustomUser.objects.create_user(
                username=employee_id,  # Use employee_id as username for consistency
                password=password,
                name=name,
                employee_id=employee_id,
                department=department,
                admin_state=admin_state,
                create_by=request.user,
                state='enable'
            )
            
            messages.success(request, f'User {name} created successfully.')
            if password.startswith('Welcome@'):
                messages.info(request, f'Default password for user: {password}')
            return redirect('login:user_list')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return render(request, 'login/user_form.html', context)
    
    return render(request, 'login/user_form.html', context)

@login_required
def user_edit(request, user_id):
    edit_user = get_object_or_404(CustomUser, id=user_id)
    
    # Limited admin can only edit normal users in their department
    if request.user.admin_state == 'no':
        if edit_user.admin_state != '-' or edit_user.department != request.user.department:
            messages.error(request, 'You do not have permission to edit this user.')
            return redirect('login:user_list')
    
    if request.method == 'POST':
        try:
            new_employee_id = request.POST.get('employee_id')
            
            # Check if employee_id is being changed
            if new_employee_id != edit_user.employee_id:
                # Check if new employee_id already exists (case-insensitive)
                if CustomUser.objects.filter(employee_id__iexact=new_employee_id).exists():
                    messages.error(request, f'Employee ID "{new_employee_id}" is already in use. Please use a different Employee ID.')
                    return render(request, 'login/user_form.html', {'edit_user': edit_user})
                
                # Update username to match new employee_id for consistency
                edit_user.username = new_employee_id
                edit_user.employee_id = new_employee_id

            edit_user.name = request.POST.get('name')
            
            # Handle department based on admin state
            if request.user.admin_state == 'yes':
                edit_user.department = request.POST.get('department')
                edit_user.admin_state = request.POST.get('admin_state', '-')
            
            # Handle state changes
            new_state = request.POST.get('state')
            if new_state and new_state != edit_user.state:
                if new_state == 'disable':
                    edit_user.disable_by = request.user.employee_id
                    edit_user.disable_datetime = timezone.now()
                    edit_user.enable_by = None
                    edit_user.enable_datetime = None
                elif new_state == 'enable' and request.user.admin_state == 'yes':  # Only admin can enable
                    edit_user.enable_by = request.user.employee_id
                    edit_user.enable_datetime = timezone.now()
                    edit_user.disable_by = None
                    edit_user.disable_datetime = None
                edit_user.state = new_state
            
            edit_user.save()
            messages.success(request, 'User updated successfully.')
            return redirect('login:user_list')
            
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
            return render(request, 'login/user_form.html', {'edit_user': edit_user})
    
    return render(request, 'login/user_form.html', {'edit_user': edit_user})

@login_required
def user_delete(request, user_id):
    user_to_disable = get_object_or_404(CustomUser, id=user_id)
    
    # Check permissions
    if request.user.admin_state == 'no':
        # Limited admin can only disable normal users in their department
        if user_to_disable.admin_state != '-' or user_to_disable.department != request.user.department:
            messages.error(request, 'You do not have permission to disable this user.')
            return redirect('login:user_list')
    elif request.user.admin_state != 'yes':
        messages.error(request, 'You do not have permission to disable users.')
        return redirect('login:user_list')
    
    # Prevent disabling yourself
    if user_to_disable == request.user:
        messages.error(request, 'You cannot disable your own account.')
        return redirect('login:user_list')
    
    if request.method == 'POST':
        try:
            user_to_disable.state = 'disable'
            user_to_disable.disable_by = request.user.employee_id
            user_to_disable.disable_datetime = timezone.now()
            user_to_disable.enable_by = None
            user_to_disable.enable_datetime = None
            user_to_disable.save()
            messages.success(request, f'User {user_to_disable.name} has been disabled successfully.')
            return redirect('login:user_list')
        except Exception as e:
            messages.error(request, f'Error disabling user: {str(e)}')
    
    return render(request, 'login/user_confirm_delete.html', {'user': user_to_disable})

@login_required
def user_bulk_add(request):
    # Only admin can access this view
    if request.user.admin_state != 'yes':
        messages.error(request, 'Only admin users can perform bulk user upload.')
        return redirect('login:user_list')
    
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'Please select a CSV file to upload.')
            return render(request, 'login/user_bulk_add.html')
        
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return render(request, 'login/user_bulk_add.html')
        
        try:
            # Read CSV file
            decoded_file = csv_file.read().decode('utf-8')
            csv_data = csv.DictReader(io.StringIO(decoded_file))
            
            success_count = 0
            error_count = 0
            errors = []
            
            for row in csv_data:
                try:
                    # Validate required fields
                    required_fields = ['employee_id', 'name', 'department']
                    if not all(row.get(field) for field in required_fields):
                        raise ValueError(f"Missing required fields for row: {row}")
                    
                    # Check if employee_id already exists
                    if CustomUser.objects.filter(username=row['employee_id']).exists():
                        raise ValueError(f"Employee ID {row['employee_id']} already exists")
                    
                    # Set default password
                    password = f"Welcome@{row['employee_id']}"
                    
                    # Create user
                    user = CustomUser.objects.create_user(
                        username=row['employee_id'],
                        password=password,
                        name=row['name'],
                        employee_id=row['employee_id'],
                        department=row['department'],
                        admin_state=row.get('admin_state', '-'),  # Default to normal user
                        create_by=request.user,
                        state='enable'
                    )
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Error in row {csv_data.line_num}: {str(e)}")
            
            if success_count > 0:
                messages.success(request, f'Successfully created {success_count} users.')
            if error_count > 0:
                messages.warning(request, f'Failed to create {error_count} users.')
                for error in errors:
                    messages.error(request, error)
            
            if success_count > 0:
                return redirect('login:user_list')
            
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
    
    return render(request, 'login/user_bulk_add.html')

@login_required
def user_bulk_delete(request):
    # Only admin users can access this view
    if request.user.admin_state != 'yes':
        messages.error(request, 'You do not have permission to bulk delete users.')
        return redirect('login:user_list')
    
    # Get all users except the current user and superusers
    users = CustomUser.objects.exclude(id=request.user.id).exclude(is_superuser=True)
    departments = CustomUser.objects.values_list('department', flat=True).distinct()
    
    if request.method == 'POST':
        user_ids = request.POST.getlist('user_ids')
        if user_ids:
            try:
                # Get selected users
                selected_users = CustomUser.objects.filter(id__in=user_ids)
                
                # Check if any selected user is a superuser or the current user
                if selected_users.filter(is_superuser=True).exists():
                    messages.error(request, 'Cannot delete superuser accounts.')
                    return redirect('login:user_bulk_delete')
                
                if str(request.user.id) in user_ids:
                    messages.error(request, 'Cannot delete your own account.')
                    return redirect('login:user_bulk_delete')
                
                # Disable the selected users
                count = selected_users.update(
                    state='disable',
                    disable_by=request.user.employee_id,
                    disable_datetime=timezone.now(),
                    enable_by=None,
                    enable_datetime=None
                )
                
                messages.success(request, f'Successfully disabled {count} user(s).')
                return redirect('login:user_list')
            except Exception as e:
                messages.error(request, f'Error disabling users: {str(e)}')
        else:
            messages.warning(request, 'No users selected for deletion.')
    
    context = {
        'users': users,
        'departments': departments
    }
    return render(request, 'login/user_bulk_delete.html', context)

# Device Management Views
@login_required
def device_list(request):
    # Get filter parameters
    state = request.GET.get('state')
    condition = request.GET.get('condition')
    
    # Base queryset based on user's admin state
    if request.user.admin_state == 'yes':
        devices = Device.objects.all()
    else:
        # Limited admin can only see devices in their department
        devices = Device.objects.filter(department=request.user.department)
    
    # Apply filters
    if state:
        devices = devices.filter(state=state)
    if condition:
        devices = devices.filter(condition=condition)
        
    # Order by serial number
    devices = devices.order_by('serial_number')
    
    context = {
        'devices': devices,
        'current_state': state,
        'current_condition': condition
    }
    return render(request, 'login/device_list.html', context)

@login_required
def device_add(request):
    if request.method == 'POST':
        try:
            # Get form data
            device_data = {
                'serial_number': request.POST.get('serial_number'),
                'make': request.POST.get('make'),
                'model': request.POST.get('model'),
                'condition': request.POST.get('condition', 'working'),
                'created_by': request.user,
                'updated_by': request.user
            }

            # Handle department based on user type
            if request.user.admin_state == 'yes':
                device_data['department'] = request.POST.get('department')
            else:
                device_data['department'] = request.user.department

            # Check for unique serial number
            if Device.objects.filter(serial_number=device_data['serial_number']).exists():
                messages.error(request, 'A device with this serial number already exists.')
                return render(request, 'login/device_form.html', {'device': None})

            # Create device
            device = Device.objects.create(**device_data)
            messages.success(request, 'Device added successfully.')
            return redirect('login:device_list')
        except Exception as e:
            messages.error(request, f'Error adding device: {str(e)}')
            return render(request, 'login/device_form.html', {'device': None})

    return render(request, 'login/device_form.html', {'device': None})

@login_required
def device_edit(request, device_id):
    device = get_object_or_404(Device, id=device_id)

    # Check permissions
    if request.user.admin_state == 'no':
        if device.department != request.user.department:
            messages.error(request, 'You do not have permission to edit this device.')
            return redirect('login:device_list')
        # Limited admin cannot edit damaged devices
        if device.condition == 'damaged':
            messages.error(request, 'Only admin can edit damaged devices.')
            return redirect('login:device_list')

    if request.method == 'POST':
        try:
            new_condition = request.POST.get('condition')
            
            # Limited admin cannot change condition from damaged to working
            if request.user.admin_state == 'no' and device.condition == 'damaged' and new_condition == 'working':
                messages.error(request, 'Only admin can change device condition from damaged to working.')
                return render(request, 'login/device_form.html', {'device': device})

            # Update device fields
            device.make = request.POST.get('make')
            device.model = request.POST.get('model')
            device.condition = new_condition
            device.updated_by = request.user

            # Only admin can change department
            if request.user.admin_state == 'yes':
                device.department = request.POST.get('department')

            device.save()
            messages.success(request, 'Device updated successfully.')
            return redirect('login:device_list')
        except Exception as e:
            messages.error(request, f'Error updating device: {str(e)}')
            return render(request, 'login/device_form.html', {'device': device})

    return render(request, 'login/device_form.html', {'device': device})

@login_required
def device_delete(request, device_id):
    # Only admin can delete devices
    if request.user.admin_state != 'yes':
        messages.error(request, 'You do not have permission to delete devices.')
        return redirect('login:device_list')

    try:
        device = Device.objects.get(id=device_id)
        
        # Check if device is assigned to any user
        active_transaction = DeviceTransaction.objects.filter(
            device=device,
            status='completed'
        ).first()
        
        if active_transaction:
            messages.error(request, f'Cannot delete device {device.serial_number} as it is currently assigned to a user.')
            return redirect('login:device_list')
        
        if request.method == 'POST':
            device.delete()
            messages.success(request, f'Device {device.serial_number} deleted successfully.')
            return redirect('login:device_list')
        
        context = {
            'device': device,
            'user': request.user,
            'page_title': 'Delete Device'
        }
        return render(request, 'login/device_confirm_delete.html', context)
        
    except Device.DoesNotExist:
        messages.error(request, 'Device not found.')
        return redirect('login:device_list')
    except Exception as e:
        messages.error(request, f'Error deleting device: {str(e)}')
        return redirect('login:device_list')

@login_required
def device_bulk_add(request):
    if request.user.admin_state != 'yes':
        messages.error(request, 'Only admin users can perform bulk device upload.')
        return redirect('login:device_list')
    
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a valid CSV file.')
                return render(request, 'login/device_bulk_add.html')
            
            try:
                # Read CSV file
                decoded_file = csv_file.read().decode('utf-8')
                csv_reader = csv.reader(io.StringIO(decoded_file))
                
                # Get headers and strip whitespace
                headers = [h.strip() for h in next(csv_reader)]
                
                success_count = 0
                error_count = 0
                errors = []
                
                for row_num, row in enumerate(csv_reader, 1):
                    try:
                        # Create a clean dictionary with stripped headers
                        row_dict = {headers[i].strip(): value.strip() for i, value in enumerate(row) if i < len(headers)}
                        
                        # Validate required fields
                        required_fields = ['serial_number', 'make', 'model', 'department']
                        if not all(field in row_dict and row_dict[field] for field in required_fields):
                            raise ValueError(f"Missing required fields for row: {row_dict}")
                        
                        # Check for duplicate serial number
                        if Device.objects.filter(serial_number=row_dict['serial_number']).exists():
                            raise ValueError(f"Serial number {row_dict['serial_number']} already exists")
                        
                        # Map status to condition if present
                        condition = row_dict.get('condition', 'working').strip().lower()
                        if condition not in ['working', 'damaged']:
                            condition = 'working'
                        
                        # Create device
                        device = Device.objects.create(
                            serial_number=row_dict['serial_number'],
                            make=row_dict['make'],
                            model=row_dict['model'],
                            department=row_dict['department'],
                            condition=condition,
                            state='stock',
                            created_by=request.user,
                            updated_by=request.user
                        )
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Error in row {row_num}: {str(e)}")
                
                if success_count > 0:
                    messages.success(request, f'Successfully created {success_count} devices.')
                if error_count > 0:
                    messages.warning(request, f'Failed to create {error_count} devices.')
                    for error in errors:
                        messages.error(request, error)
                
                if success_count > 0:
                    return redirect('login:device_list')
                
            except Exception as e:
                messages.error(request, f'Error processing CSV file: {str(e)}')
                return render(request, 'login/device_bulk_add.html')
        
        # Handle JSON data
        else:
            try:
                devices_data = []
                # Try to get data from POST first
                raw_data = request.POST.get('devices')
                if raw_data:
                    devices_data = json.loads(raw_data)
                # If not in POST, try to get from body
                elif request.body:
                    data = json.loads(request.body)
                    devices_data = data.get('devices', [])
                
                if not devices_data:
                    return JsonResponse({
                        'success': False,
                        'message': 'No device data provided'
                    })
                
                if not isinstance(devices_data, list):
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid data format. Expected a list of devices.'
                    })
                
                created_devices = []
                errors = []
                
                for i, device_data in enumerate(devices_data, 1):
                    try:
                        # Clean the data by stripping whitespace
                        device_data = {k.strip(): v.strip() if isinstance(v, str) else v 
                                     for k, v in device_data.items()}
                        
                        # Validate required fields
                        if not all(k in device_data for k in ['serial_number', 'make', 'model', 'department']):
                            errors.append(f"Error in row {i}: Missing required fields")
                            continue
                        
                        # Check for duplicate serial number
                        if Device.objects.filter(serial_number=device_data['serial_number']).exists():
                            errors.append(f"Error in row {i}: Serial number {device_data['serial_number']} already exists")
                            continue
                        
                        # Map status to condition if present
                        condition = device_data.get('condition', 'working').lower()
                        if condition not in ['working', 'damaged']:
                            condition = 'working'
                        
                        # Create device
                        device = Device.objects.create(
                            serial_number=device_data['serial_number'],
                            make=device_data['make'],
                            model=device_data['model'],
                            department=device_data['department'],
                            condition=condition,
                            state='stock',
                            created_by=request.user,
                            updated_by=request.user
                        )
                        created_devices.append(device)
                        
                    except Exception as e:
                        errors.append(f"Error in row {i}: {str(e)}")
                
                if errors:
                    return JsonResponse({
                        'success': False,
                        'message': 'Some devices could not be added',
                        'errors': errors,
                        'created_count': len(created_devices)
                    })
                
                return JsonResponse({
                    'success': True,
                    'message': f'Successfully added {len(created_devices)} devices',
                    'created_count': len(created_devices)
                })
                
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid JSON data'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error processing request: {str(e)}'
                })
    
    return render(request, 'login/device_bulk_add.html')

@login_required
def device_bulk_delete(request):
    # Only admin can delete devices
    if request.user.admin_state != 'yes':
        messages.error(request, 'You do not have permission to delete devices.')
        return redirect('login:device_list')

    if request.method == 'POST':
        try:
            # Get selected device IDs from the form
            device_ids = request.POST.getlist('device_ids')
            if not device_ids:
                messages.error(request, 'No devices selected for deletion.')
                return redirect('login:device_bulk_delete')

            # Convert string IDs to integers
            device_ids = [int(id) for id in device_ids]
            
            # Get devices and check if any are assigned
            devices = Device.objects.filter(id__in=device_ids)
            assigned_devices = []
            
            for device in devices:
                if device.state == 'assigned':
                    assigned_devices.append(device.serial_number)
            
            if assigned_devices:
                messages.error(request, f'Cannot delete devices that are currently assigned: {", ".join(assigned_devices)}')
                return redirect('login:device_bulk_delete')
            
            # Delete devices
            delete_count = devices.count()
            devices.delete()
            messages.success(request, f'Successfully deleted {delete_count} device(s).')
            return redirect('login:device_list')
            
        except Exception as e:
            messages.error(request, f'Error deleting devices: {str(e)}')
            return redirect('login:device_bulk_delete')
    
    # GET request - show the bulk delete page
    # Get all devices that are not assigned
    devices = Device.objects.exclude(state='assigned')
    
    # Get unique departments for filtering
    departments = devices.values_list('department', flat=True).distinct().order_by('department')
    
    context = {
        'devices': devices,
        'departments': departments,
        'user': request.user,
        'page_title': 'Bulk Delete Devices'
    }
    return render(request, 'login/device_bulk_delete.html', context)

@login_required
def update_all_devices_to_working(request):
    if request.user.admin_state != 'yes':
        messages.error(request, 'Only admin users can perform this action.')
        return redirect('login:device_list')
    
    try:
        # Get all devices
        devices = Device.objects.all()
        total_devices = devices.count()
        
        # Update all devices to working condition
        updated_count = devices.update(condition='working')
        
        messages.success(request, f'Successfully updated {updated_count} out of {total_devices} devices to working condition')
    except Exception as e:
        messages.error(request, f'Error updating devices: {str(e)}')
    
    return redirect('login:device_list')

# Handover/Takeover Views
# @login_required
# def handover_create(request):
#     from dashboard.forms import HandoverForm
    
#     if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no']):
#         logout(request)
#         return redirect('login:login')
        
#     if request.method == 'POST':
#         form = HandoverForm(request.POST, user=request.user)
#         if form.is_valid():
#             try:
#                 # Get the device and employee
#                 device = Device.objects.get(serial_number=form.cleaned_data['device_serial_number'])
#                 employee = CustomUser.objects.get(employee_id=form.cleaned_data['employee_id'])
                
#                 # Check if device is in stock state
#                 if device.state != 'stock':
#                     form.add_error('device_serial_number', "Device must be in stock state for handover.")
#                     return render(request, 'login/handover_form.html', {'form': form, 'page_title': 'Create Handover'})
                
#                 # Create handover record with device's current condition
#                 handover = HandoverTakeover.objects.create(
#                     device=device,
#                     from_user=request.user,
#                     to_user=employee,
#                     transaction_type='handover',
#                     device_condition=device.condition,  # Use device's current condition
#                     created_by=request.user
#                 )
                
#                 # Update device state and maintain current condition
#                 device.state = 'assigned'
#                 device.assigned_to = employee
#                 device.updated_by = request.user
#                 device.save()
                
#                 messages.success(request, f'Device {device.serial_number} successfully handed over to {employee.employee_id}.')
                
#                 # Redirect to handover list page
#                 return redirect('login:handover_list')
                
#             except Device.DoesNotExist:
#                 form.add_error('device_serial_number', "Device not found.")
#             except CustomUser.DoesNotExist:
#                 form.add_error('employee_id', "Employee not found.")
#             except Exception as e:
#                 messages.error(request, f"Error creating handover: {str(e)}")
#         else:
#             for field in form.errors:
#                 for error in form.errors[field]:
#                     messages.error(request, f"{field}: {error}")
#     else:
#         # Get device ID from query parameter if available
#         device_id = request.GET.get('device')
#         initial = {}
#         if device_id:
#             try:
#                 device = Device.objects.get(id=device_id)
#                 initial = {
#                     'device_serial_number': device.serial_number,
#                     'device_condition': device.condition  # Pre-fill with device's current condition
#                 }
#             except Device.DoesNotExist:
#                 pass
#         form = HandoverForm(user=request.user, initial=initial)
    
#     context = {
#         'form': form,
#         'page_title': 'Create Handover'
#     }
#     return render(request, 'login/handover_form.html', context)

@login_required
def handover_create(request):
    from dashboard.forms import HandoverForm
    
    if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no']):
        logout(request)
        return redirect('login:login')
        
    if request.method == 'POST':
        form = HandoverForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                # Get the device and employee
                device = Device.objects.get(serial_number=form.cleaned_data['device_serial_number'])
                employee = CustomUser.objects.get(employee_id=form.cleaned_data['employee_id'])
                
                # Check if device is in stock state
                if device.state != 'stock':
                    form.add_error('device_serial_number', "Device must be in stock state for handover.")
                    return render(request, 'login/handover_form.html', {'form': form, 'page_title': 'Create Handover'})
                
                # Create handover record with device's current condition
                handover = HandoverTakeover.objects.create(
                    device=device,
                    from_user=request.user,
                    to_user=employee,
                    transaction_type='handover',
                    device_condition=device.condition,
                    created_by=request.user
                )
                
                # Update device state and assigned user
                device.state = 'assigned'
                device.assigned_to = employee
                device.updated_by = request.user
                device.save()
                
                # Show success message and render the same form again (reset)
                messages.success(request, f'Device {device.serial_number} successfully handed over to {employee.employee_id}.')
                form = HandoverForm(user=request.user)  # reset form
                return render(request, 'login/handover_form.html', {
                    'form': form,
                    'page_title': 'Create Handover'
                })
                
            except Device.DoesNotExist:
                form.add_error('device_serial_number', "Device not found.")
            except CustomUser.DoesNotExist:
                form.add_error('employee_id', "Employee not found.")
            except Exception as e:
                messages.error(request, f"Error creating handover: {str(e)}")
        else:
            for field in form.errors:
                for error in form.errors[field]:
                    messages.error(request, f"{field}: {error}")
    else:
        # Get device ID from query parameter if available
        device_id = request.GET.get('device')
        initial = {}
        if device_id:
            try:
                device = Device.objects.get(id=device_id)
                initial = {
                    'device_serial_number': device.serial_number,
                    'device_condition': device.condition
                }
            except Device.DoesNotExist:
                pass
        form = HandoverForm(user=request.user, initial=initial)
    
    context = {
        'form': form,
        'page_title': 'Create Handover'
    }
    return render(request, 'login/handover_form.html', context)


@login_required
def handover_list(request):
    handovers = HandoverTakeover.objects.all()
    return render(request, 'login/handover_list.html', {'handovers': handovers})

@login_required
def handover_acknowledge(request, handover_id):
    handover = get_object_or_404(HandoverTakeover, id=handover_id)
    if request.method == 'POST':
        handover.acknowledged = True
        handover.acknowledged_at = timezone.now()
        handover.save()
        messages.success(request, 'Handover acknowledged successfully.')
        return redirect('login:handover_list')
    
    return render(request, 'login/handover_acknowledge.html', {'handover': handover})

@login_required
def takeover_create(request):
    if request.method == 'POST':
        form = TakeoverForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                device = Device.objects.get(serial_number=form.cleaned_data['device_serial_number'])
                
                # Get the device condition from the form or use the current condition
                device_condition = form.cleaned_data.get('device_condition', device.condition)
                
                # Create takeover transaction
                takeover = HandoverTakeover.objects.create(
                    device=device,
                    from_user=device.assigned_to,
                    to_user=request.user,
                    transaction_type='takeover',
                    device_condition=device_condition,
                    created_by=request.user
                )
                
                # Update device condition
                device.condition = device_condition
                device.updated_by = request.user
                
                # If device is marked as damaged, update damage info
                if device_condition == 'damaged':
                    device.damage_by = request.user
                    device.damage_date = timezone.now()
                    if 'damage_info' in form.cleaned_data:
                        device.damage_info = form.cleaned_data['damage_info']
                
                # Update device state
                device.state = 'stock'
                device.assigned_to = None
                device.save()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Device takeover created successfully'
                    })
                return redirect('login:transactions')
            except Device.DoesNotExist:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'Device not found'
                    })
                form.add_error('device_serial_number', 'Device not found')
    else:
        form = TakeoverForm(user=request.user)
    
    return render(request, 'login/takeover_form.html', {'form': form})

@login_required
def get_device(request, search_value):
    try:
        device = Device.objects.get(serial_number=search_value)
        return JsonResponse({
            'device': {
                'serial_number': device.serial_number,
                'state': device.state,
                'condition': device.condition,
                'make': device.make,
                'model': device.model,
                'department': device.department
            }
        })
    except Device.DoesNotExist:
        return JsonResponse({
            'error': 'Device not found',
            'device': None
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'device': None
        }, status=500)

def get_employee(request, search_value):
    try:
        employee = CustomUser.objects.get(employee_id=search_value)
        return JsonResponse({
            'employee': {
                'employee_id': employee.employee_id,
                'name': employee.name
            }
        })
    except CustomUser.DoesNotExist:
        return JsonResponse({'employee': None})

@login_required
def transactions(request):
    if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no', '-']):
        logout(request)
        return redirect('login:login')
    
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    transaction_type = request.GET.get('transaction_type')
    download = request.GET.get('download')
    
    # Get all transactions ordered by date
    transactions = HandoverTakeover.objects.all().order_by('-transaction_date')
    
    # Apply filters
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        transactions = transactions.filter(transaction_date__gte=start_date)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        transactions = transactions.filter(transaction_date__lte=end_date)
    
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # Process transactions to show status at the time of transaction
    processed_transactions = []
    for transaction in transactions:
        # Get the status before this transaction
        previous_transaction = HandoverTakeover.objects.filter(
            device=transaction.device,
            transaction_date__lt=transaction.transaction_date
        ).order_by('-transaction_date').first()
        
        if previous_transaction:
            status_before = 'assigned' if previous_transaction.transaction_type == 'handover' else 'stock'
        else:
            status_before = 'stock'  # Default status for first transaction
        
        # Get the status after this transaction
        status_after = 'assigned' if transaction.transaction_type == 'handover' else 'stock'
        
        processed_transactions.append({
            'transaction': transaction,
            'status_before': status_before,
            'status_after': status_after
        })
    
    # Handle CSV download
    if download:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Type', 'Device', 'From', 'To', 'Status', 'Status Before', 'Status After', 'Created By'
        ])
        
        for trans in processed_transactions:
            writer.writerow([
                trans['transaction'].transaction_date.strftime('%Y-%m-%d %H:%M'),
                trans['transaction'].transaction_type.title(),
                trans['transaction'].device.serial_number,
                f"{trans['transaction'].from_user.name} ({trans['transaction'].from_user.employee_id})",
                f"{trans['transaction'].to_user.name} ({trans['transaction'].to_user.employee_id})",
                trans['transaction'].device_condition.title(),
                trans['status_before'].title(),
                trans['status_after'].title(),
                f"{trans['transaction'].created_by.name} ({trans['transaction'].created_by.employee_id})"
            ])
        
        return response
    
    context = {
        'transactions': processed_transactions,
    }
    return render(request, 'login/transactions.html', context)

def custom_404(request, exception):
    if request.user.is_authenticated:
        return redirect('login:dashboard')
    else:
        return redirect('login:login')
