from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Company, Role


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'company_type',
        'is_active',
        'created_at',
    )

    list_filter = (
        'company_type',
        'is_active',
    )

    search_fields = (
        'name',
    )

    ordering = ('name',)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'code',
    )

    search_fields = (
        'name',
        'code',
    )

    ordering = ('name',)
    VERBOSE_NAME = 'دور المستخدم'
    VERBOSE_NAME_PLURAL = 'أدوار المستخدمين'

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'company',
        'role',
        'is_active',
        'is_staff',
    )

    list_filter = (
        'company',
        'role',
        'is_active',
        'is_staff',
    )

    fieldsets = UserAdmin.fieldsets + (
        ('بيانات العمل', {
            'fields': (
                'company',
                'role',
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('بيانات العمل', {
            'fields': (
                'company',
                'role',
            )
        }),
    )

    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
    )

    ordering = ('username',)
