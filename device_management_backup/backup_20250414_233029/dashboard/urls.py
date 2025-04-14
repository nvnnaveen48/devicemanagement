from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('add-user/', views.add_user, name='add_user'),
    path('show-users/', views.show_users, name='show_users'),
    path('delete-user/', views.delete_user, name='delete_user'),
    path('devices-inventory/', views.devices_inventory, name='devices_inventory'),
    path('devices-sheet/', views.devices_sheet, name='devices_sheet'),
    path('handover/', views.handover, name='handover'),
    path('takeover/', views.takeover, name='takeover'),
    path('get-device-status/<str:serial_number>/', views.get_device_status, name='get_device_status'),
] 