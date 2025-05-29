from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser

class CustomUserAdmin(BaseUserAdmin):
    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'role', 'status', 'is_staff')
    list_filter = ('role', 'status', 'is_staff', 'is_superuser')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number', 'picture')}),
        ('Roles & Permissions', {'fields': ('role', 'status', 'email_verified', 'email_verification_code' , 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('API Keys', {'fields': ('api_key', 'chatBot_key', 'chatBot_user_id')}),
        ('User Info', {'fields': ('sizeOfCompany', 'opt_terms')}),
        ('Important Dates', {'fields': ('last_login',)}),
        ('Lofty Info', {'fields': ('lofty_user_id', 'lofty_access_token', 'lofty_refresh_token', 'lofty_token_expires_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )

    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

admin.site.register(CustomUser, CustomUserAdmin)
# Register your models here.