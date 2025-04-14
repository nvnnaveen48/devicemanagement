from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from login.models import CustomUser, Device
from django.utils import timezone
from django.http import JsonResponse
from .forms import HandoverForm, TakeoverForm
from .models import DeviceTransaction

@login_required
def home(request):
    if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no']):
        logout(request)
        return redirect('login:login')
    
    context = {
        'user': request.user,
        'page_title': 'Dashboard'
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def add_user(request):
    if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no']):
        logout(request)
        return redirect('login:login')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        name = request.POST.get('name')
        employee_id = request.POST.get('employee_id')
        admin_state = request.POST.get('admin_state', '-')
        
        # Only admin with 'yes' state can create admin users
        if admin_state == 'yes' and request.user.admin_state != 'yes':
            messages.error(request, 'You do not have permission to create admin users.')
            admin_state = '-'
        
        try:
            user = CustomUser.objects.create_user(
                username=username,
                password=password,
                name=name,
                employee_id=employee_id,
                admin_state=admin_state,
                state='enable',
                create_by=request.user,
                enable_by=request.user
            )
            messages.success(request, f'User {username} created successfully!')
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
    
    context = {
        'user': request.user,
        'page_title': 'Add User',
        'can_create_admin': request.user.admin_state == 'yes'
    }
    return render(request, 'dashboard/add_user.html', context)

@login_required
def show_users(request):
    if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no']):
        logout(request)
        return redirect('login:login')
    
    # Only show enabled users unless the viewer is an admin
    if request.user.admin_state == 'yes':
        users = CustomUser.objects.all().order_by('username')
    else:
        users = CustomUser.objects.filter(state='enable').order_by('username')
    
    context = {
        'user': request.user,
        'page_title': 'Show Users',
        'users': users
    }
    return render(request, 'dashboard/show_users.html', context)

@login_required
def delete_user(request):
    if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no']):
        logout(request)
        return redirect('login:login')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        try:
            user = CustomUser.objects.get(id=user_id)
            if user != request.user:  # Prevent self-deletion
                # Check if trying to disable an admin
                if user.admin_state == 'yes' and request.user.admin_state != 'yes':
                    messages.error(request, 'You do not have permission to disable admin users!')
                else:
                    user.state = 'disable'
                    user.disable_by = request.user
                    user.save()
                    messages.success(request, f'User {user.username} has been disabled!')
            else:
                messages.error(request, 'You cannot disable your own account!')
        except CustomUser.DoesNotExist:
            messages.error(request, 'User not found!')
    
    # Only show enabled users unless the viewer is an admin
    if request.user.admin_state == 'yes':
        users = CustomUser.objects.all().order_by('username')
    else:
        users = CustomUser.objects.filter(state='enable').order_by('username')
    
    context = {
        'user': request.user,
        'page_title': 'Delete User',
        'users': users
    }
    return render(request, 'dashboard/delete_user.html', context)

@login_required
def enable_user(request):
    if not (request.user.state == 'enable' and request.user.admin_state == 'yes'):
        logout(request)
        return redirect('login:login')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        try:
            user = CustomUser.objects.get(id=user_id)
            user.state = 'enable'
            user.enable_by = request.user
            user.save()
            messages.success(request, f'User {user.username} has been enabled!')
        except CustomUser.DoesNotExist:
            messages.error(request, 'User not found!')
    
    users = CustomUser.objects.filter(state='disable').order_by('username')
    context = {
        'user': request.user,
        'page_title': 'Enable Users',
        'users': users
    }
    return render(request, 'dashboard/enable_user.html', context)

@login_required
def devices_inventory(request):
    if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no', '-']):
        logout(request)
        return redirect('login:login')
    
    context = {
        'user': request.user,
        'page_title': 'Devices Inventory'
    }
    return render(request, 'dashboard/devices_inventory.html', context)

@login_required
def devices_sheet(request):
    if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no', '-']):
        logout(request)
        return redirect('login:login')
    
    context = {
        'user': request.user,
        'page_title': 'Devices Sheet'
    }
    return render(request, 'dashboard/devices_sheet.html', context)

@login_required
def get_device_status(request, serial_number):
    try:
        device = Device.objects.get(serial_number=serial_number)
        return JsonResponse({'status': device.status})
    except Device.DoesNotExist:
        return JsonResponse({'status': None}, status=404)

@login_required
def handover(request):
    if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no']):
        logout(request)
        return redirect('login:login')
    
    # Get all handed over devices
    handed_over_devices = DeviceTransaction.objects.filter(
        status='completed'
    ).order_by('-handover_datetime')
    
    if request.method == 'POST':
        form = HandoverForm(request.POST)
        if form.is_valid():
            try:
                # Get the cleaned data
                device = form.cleaned_data['device_serial_number']
                user = form.cleaned_data['employee_id']
                device_status = form.cleaned_data['device_status']
                
                # Check if device is already assigned
                existing_transaction = DeviceTransaction.objects.filter(
                    device=device,
                    status='completed'
                ).first()
                
                if existing_transaction:
                    messages.error(request, 'Device is already assigned to another user')
                    return redirect('dashboard:transactions')
                
                # Create new transaction
                transaction = DeviceTransaction.objects.create(
                    device=device,
                    device_serial_number=device.serial_number,
                    user=user,
                    user_name=user.name,
                    device_status=device_status,
                    handover_by=request.user,
                    handover_datetime=timezone.now()
                )
                
                # Update device status
                device.status = 'assigned'
                device.save()
                
                messages.success(request, 'Device handover successful!')
                return redirect('dashboard:transactions')
                
            except Exception as e:
                messages.error(request, f'Error during handover: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = HandoverForm()
    
    context = {
        'user': request.user,
        'page_title': 'Handover',
        'form': form,
        'handed_over_devices': handed_over_devices
    }
    return render(request, 'dashboard/handover.html', context)

@login_required
def takeover(request):
    if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no', '-']):
        logout(request)
        return redirect('login:login')
    
    if request.method == 'POST':
        form = TakeoverForm(request.POST)
        if form.is_valid():
            try:
                # Get the device
                device = Device.objects.get(serial_number=form.cleaned_data['device_serial_number'])
                
                # Get the current user of the device
                current_transaction = DeviceTransaction.objects.filter(
                    device=device,
                    device__status='assigned'
                ).exclude(
                    transaction_type='takeover'
                ).first()
                
                if not current_transaction:
                    messages.error(request, "Device is not assigned to any user.")
                    return redirect('dashboard:transactions')
                
                # Create the takeover transaction
                transaction = DeviceTransaction.objects.create(
                    device=device,
                    from_user=current_transaction.to_user,  # Current device holder
                    to_user=request.user,  # Admin taking over
                    transaction_type='takeover',
                    condition=form.cleaned_data['device_status'],
                    created_by=request.user
                )
                
                # Update device status based on condition
                if form.cleaned_data['device_status'] == 'damaged':
                    device.status = 'damaged'
                else:
                    device.status = 'stock'
                device.save()
                
                messages.success(request, f"Device {device.serial_number} has been taken over and is now {device.status}.")
                return redirect('dashboard:transactions')
                
            except Device.DoesNotExist:
                messages.error(request, "Device not found.")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        form = TakeoverForm()
    
    context = {
        'user': request.user,
        'page_title': 'Takeover',
        'form': form
    }
    return render(request, 'dashboard/takeover.html', context)

@login_required
def logout_view(request):
    logout(request)
    return redirect('login:login')

@login_required
def handover_create(request):
    if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no']):
        logout(request)
        return redirect('login:login')
        
    if request.method == 'POST':
        form = HandoverForm(request.POST)
        if form.is_valid():
            try:
                # Get the device and user
                device = Device.objects.get(serial_number=form.cleaned_data['device_serial_number'])
                to_user = CustomUser.objects.get(employee_id=form.cleaned_data['employee_id'])
                
                # Check if user is disabled
                if to_user.state == 'disable':
                    messages.error(request, "Cannot handover device to a disabled user.")
                    return redirect('dashboard:transactions')
                
                # Check if user already has a device
                active_transaction = DeviceTransaction.objects.filter(
                    to_user=to_user,
                    device__status='assigned'
                ).exclude(
                    transaction_type='takeover'
                ).first()
                
                if active_transaction:
                    messages.error(request, f"User already has device {active_transaction.device.serial_number} assigned to them.")
                    return redirect('dashboard:transactions')
                
                # Create the handover transaction
                transaction = DeviceTransaction.objects.create(
                    device=device,
                    from_user=request.user,
                    to_user=to_user,
                    transaction_type='handover',
                    condition=form.cleaned_data['device_status'],
                    created_by=request.user
                )
                
                # Update device status
                device.status = 'assigned'
                device.save()
                
                messages.success(request, f"Device {device.serial_number} successfully handed over to {to_user.name}.")
                return redirect('dashboard:transactions')
                
            except Device.DoesNotExist:
                messages.error(request, "Device not found.")
            except CustomUser.DoesNotExist:
                messages.error(request, "User not found.")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        form = HandoverForm()
    
    context = {
        'user': request.user,
        'page_title': 'Create Handover',
        'form': form
    }
    return render(request, 'dashboard/handover_create.html', context)

@login_required
def transactions(request):
    if not (request.user.state == 'enable' and request.user.admin_state in ['yes', 'no', '-']):
        logout(request)
        return redirect('login:login')
    
    # Get all transactions ordered by date
    transactions = DeviceTransaction.objects.all().order_by('-transaction_date')
    
    # Process transactions to show status changes
    processed_transactions = []
    for transaction in transactions:
        # Get the actual device status before and after the transaction
        status_before = transaction.device.status
        status_after = transaction.device_status if transaction.device_status else status_before
        
        processed_transactions.append({
            'transaction_date': transaction.transaction_date,
            'device': transaction.device,
            'transaction_type': transaction.transaction_type,
            'from_user': transaction.from_user,
            'to_user': transaction.to_user,
            'status_before': status_before,
            'status_after': status_after,
            'condition': transaction.condition,
            'acknowledged': transaction.acknowledged
        })
    
    context = {
        'user': request.user,
        'page_title': 'Transactions',
        'transactions': processed_transactions
    }
    return render(request, 'dashboard/transactions.html', context)
