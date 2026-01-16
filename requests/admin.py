from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    RequestType,
    RequestField,
    Request,
    RequestFieldValue,
)


# =========================
# Request Type
# =========================
@admin.register(RequestType)
class RequestTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("name",)


# =========================
# Request Field
# =========================
@admin.register(RequestField)
class RequestFieldAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "key",
        "request_type",
        "field_type",
        "is_required",
        "is_active",
        "sort_order",
    )
    list_filter = (
        "request_type",
        "field_type",
        "is_required",
        "is_active",
    )
    search_fields = ("label", "key")
    ordering = ("request_type", "sort_order")


# =========================
# Inline: Field Values
# =========================
class RequestFieldValueInline(admin.TabularInline):
    model = RequestFieldValue
    extra = 0
    can_delete = False

    readonly_fields = (
        "field",
        "value_text",
        "value_number",
        "value_date",
        "value_bool",
        "value_json",
    )

    def has_add_permission(self, request, obj=None):
        return False


# =========================
# Request Admin
# =========================
@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "request_type",
        "worker",
        "status",
        "current_company",
        "created_by",
        "created_at",
        "closed_at",
    )

    list_filter = (
        "status",
        "request_type",
        "current_company",
    )

    search_fields = (
        "id",
        "worker__full_name",
        "worker__iqama_number",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
        "updated_at",
        "closed_at",
        "closed_by",
    )

    inlines = [RequestFieldValueInline]

    fieldsets = (
        ("بيانات الطلب", {
            "fields": (
                "request_type",
                "worker",
                "status",
                "current_company",
            )
        }),
        ("ملاحظات", {
            "fields": (
                "title",
                "notes",
            )
        }),
        ("قرار الإغلاق (شركة التوريد فقط)", {
            "fields": (
                "rejection_reason",
                "closure_note",
                "closed_by",
                "closed_at",
            )
        }),
        ("معلومات النظام", {
            "fields": (
                "created_by",
                "created_at",
                "updated_at",
            )
        }),
    )

    # =========================
    # Validation in Admin
    # =========================
    def save_model(self, request, obj, form, change):
        """
        قواعد صارمة:
        - عند completed / rejected:
          - يتم تسجيل closed_at تلقائيًا إن لم يكن موجود
          - يتم تسجيل closed_by تلقائيًا
        - عند rejected:
          - سبب الرفض إلزامي
        """

        if obj.status in ("completed", "rejected"):
            if not obj.closed_at:
                obj.closed_at = timezone.now()

            if not obj.closed_by:
                obj.closed_by = request.user

            if obj.status == "rejected" and not obj.rejection_reason:
                raise ValidationError(
                    "لا يمكن رفض الطلب بدون ذكر سبب الرفض."
                )

        super().save_model(request, obj, form, change)

    # =========================
    # Hide assigned_to completely
    # =========================
    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        return [f for f in fields if f != "assigned_to"]

