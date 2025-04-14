from django.urls import path
from . import views

app_name = 'login'

# Add handler404 configuration
handler404 = views.custom_404

urlpatterns = [
    # Authentication
    path('', views.login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # User Management
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_add, name='user_add'),
    path('users/edit/<int:user_id>/', views.user_edit, name='user_edit'),
    path('users/delete/<int:user_id>/', views.user_delete, name='user_delete'),
    path('users/bulk-add/', views.user_bulk_add, name='user_bulk_add'),
    
    # Device Management
    path('devices/', views.device_list, name='device_list'),
    path('devices/add/', views.device_add, name='device_add'),
    path('devices/edit/<int:device_id>/', views.device_edit, name='device_edit'),
    path('devices/delete/<int:device_id>/', views.device_delete, name='device_delete'),
    path('devices/bulk-add/', views.device_bulk_add, name='device_bulk_add'),
    path('devices/bulk-delete/', views.device_bulk_delete, name='device_bulk_delete'),
    path('device/update-all-to-working/', views.update_all_devices_to_working, name='update_all_devices_to_working'),
    
    # Handover/Takeover
    path('handover/create/', views.handover_create, name='handover_create'),
    path('handover/list/', views.handover_list, name='handover_list'),
    path('handover/acknowledge/<int:handover_id>/', views.handover_acknowledge, name='handover_acknowledge'),
    path('takeover/create/', views.takeover_create, name='takeover_create'),
    path('transactions/', views.transactions, name='transactions'),
    path('get_device/<str:search_value>/', views.get_device, name='get_device'),
] 