from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Profile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'email', 'last_name', 'postnom', 'first_name',
        'whatsapp_number', 'is_participant', 'is_staff', 'is_active',
    )
    list_filter = ('is_participant', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('email', 'last_name', 'postnom', 'first_name', 'whatsapp_number')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Identité'), {'fields': ('last_name', 'postnom', 'first_name', 'whatsapp_number')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_participant', 'groups', 'user_permissions'),
        }),
        (_('Dates importantes'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'last_name', 'postnom', 'first_name',
                'whatsapp_number', 'password1', 'password2',
            ),
        }),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_verified', 'last_login_ip', 'created_at')
    list_filter = ('email_verified',)
    search_fields = ('user__email', 'user__last_name', 'user__postnom')
    readonly_fields = ('created_at', 'updated_at')