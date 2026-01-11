from django.contrib import admin
from .models import Vendor, Worker


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = (
        'company',
        'contact_name',
        'contact_phone',
        'is_active',
    )

    list_filter = (
        'is_active',
    )

    search_fields = (
        'company__name',
        'contact_name',
        'contact_phone',
    )

    ordering = ('company__name',)


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'iqama_number',
        'vendor',
        'insurance_class',
        'status',
        'iqama_expiry_date',
    )

    list_filter = (
        'vendor',
        'insurance_class',
        'status',
    )

    search_fields = (
        'full_name',
        'iqama_number',
    )

    ordering = ('full_name',)

    date_hierarchy = 'iqama_expiry_date'
