from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'name', 'employee_id', 'state', 'admin_state', 'create_datetime')
    list_filter = ('state', 'admin_state', 'create_datetime')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('name', 'employee_id', 'email')}),
        ('Permissions', {'fields': ('state', 'admin_state', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'name', 'employee_id', 'password1', 'password2'),
        }),
    )
    search_fields = ('username', 'name', 'employee_id')
    ordering = ('username',)

admin.site.register(CustomUser, CustomUserAdmin)
