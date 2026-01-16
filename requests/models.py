from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import Company
from vendors.models import Worker

User = settings.AUTH_USER_MODEL


# =========================
# Request Type
# =========================
class RequestType(models.Model):
    name = models.CharField(
        max_length=150,
        verbose_name="اسم نوع الطلب"
    )

    code = models.SlugField(
        max_length=80,
        unique=True,
        verbose_name="الكود"
    )

    description = models.TextField(
        blank=True,
        verbose_name="الوصف"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "نوع طلب"
        verbose_name_plural = "أنواع الطلبات"
        ordering = ("name",)

    def __str__(self):
        return self.name


# =========================
# Request Field (Dynamic)
# =========================
class RequestField(models.Model):
    FIELD_TYPE_CHOICES = (
        ("text", "نص"),
        ("number", "رقم"),
        ("date", "تاريخ"),
        ("bool", "نعم / لا"),
        ("choice", "قائمة خيارات"),
        ("json", "بيانات مركبة"),
    )

    request_type = models.ForeignKey(
        RequestType,
        on_delete=models.CASCADE,
        related_name="fields",
        verbose_name="نوع الطلب"
    )

    label = models.CharField(
        max_length=150,
        verbose_name="اسم الحقل (للعرض)"
    )

    key = models.SlugField(
        max_length=80,
        verbose_name="مفتاح الحقل"
    )

    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        verbose_name="نوع الحقل"
    )

    is_required = models.BooleanField(
        default=False,
        verbose_name="إلزامي"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="مفعل"
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتيب العرض"
    )

    help_text = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="مساعدة"
    )

    # للحقول من نوع choice
    choices = models.JSONField(
        null=True,
        blank=True,
        verbose_name="الخيارات"
    )

    class Meta:
        verbose_name = "حقل طلب"
        verbose_name_plural = "حقول الطلبات"
        ordering = ("request_type", "sort_order")
        constraints = [
            models.UniqueConstraint(
                fields=["request_type", "key"],
                name="uq_requestfield_type_key"
            )
        ]

    def __str__(self):
        return f"{self.request_type.code} :: {self.label}"

    def clean(self):
        if self.field_type == "choice" and not self.choices:
            raise ValidationError({
                "choices": "يجب تحديد الخيارات عند استخدام نوع الحقل (قائمة خيارات)."
            })


# =========================
# Request (Core Entity)
# =========================
class Request(models.Model):
    STATUS_CHOICES = (
        ("draft", "مسودة"),
        ("submitted", "مرسل"),
        ("in_progress", "قيد المعالجة"),
        ("returned", "معاد (لوجود نقص)"),
        ("completed", "مكتمل"),
        ("rejected", "مرفوض"),
        ("cancelled", "ملغي"),
    )

    request_type = models.ForeignKey(
        RequestType,
        on_delete=models.PROTECT,
        related_name="requests",
        verbose_name="نوع الطلب"
    )

    worker = models.ForeignKey(
        Worker,
        on_delete=models.PROTECT,
        related_name="requests",
        verbose_name="العامل"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        verbose_name="الحالة"
    )

    title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="عنوان مختصر"
    )

    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_requests",
        verbose_name="أُنشئ بواسطة"
    )

    # موجود في قاعدة البيانات فقط – غير مستخدم حاليًا
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_requests",
        verbose_name="مسند إلى (غير مفعل حاليًا)"
    )

    current_company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="current_requests",
        verbose_name="الجهة الحالية المسؤولة"
    )

    # ===== قرار الإغلاق النهائي (من شركة التوريد فقط) =====
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="سبب الرفض"
    )

    closure_note = models.TextField(
        blank=True,
        verbose_name="ملاحظة الإغلاق"
    )

    return_reason = models.TextField(blank=True, null=True, verbose_name="سبب الإعادة/النقص")

    closed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_requests",
        verbose_name="أُغلق بواسطة"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخر تحديث"
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاريخ الإغلاق"
    )

    class Meta:
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["request_type"]),
            models.Index(fields=["worker"]),
        ]

    def __str__(self):
        return f"طلب #{self.id} - {self.request_type.name}"

    def clean(self):
        # عند الإرسال أو المعالجة يجب تحديد الجهة الحالية
        if self.status in ("submitted", "in_progress") and not self.current_company:
            raise ValidationError({
                "current_company": "يجب تحديد الجهة الحالية المسؤولة."
            })

        # عند الرفض يجب ذكر السبب
        if self.status == "rejected" and not self.rejection_reason:
            raise ValidationError({
                "rejection_reason": "سبب الرفض إلزامي."
            })

        # عند الإغلاق النهائي (مكتمل / مرفوض)
        if self.status in ("completed", "rejected"):
            if not self.closed_at:
                raise ValidationError({
                    "closed_at": "يجب تحديد تاريخ الإغلاق."
                })
            if not self.closed_by:
                raise ValidationError({
                    "closed_by": "يجب تحديد من قام بالإغلاق."
                })


# =========================
# Request Field Value
# =========================
class RequestFieldValue(models.Model):
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name="field_values",
        verbose_name="الطلب"
    )

    field = models.ForeignKey(
        RequestField,
        on_delete=models.PROTECT,
        related_name="values",
        verbose_name="الحقل"
    )

    value_text = models.TextField(
        null=True,
        blank=True,
        verbose_name="قيمة نصية"
    )

    value_number = models.DecimalField(
        null=True,
        blank=True,
        max_digits=12,
        decimal_places=2,
        verbose_name="قيمة رقمية"
    )

    value_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="قيمة تاريخ"
    )

    value_bool = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="قيمة نعم / لا"
    )

    value_json = models.JSONField(
        null=True,
        blank=True,
        verbose_name="قيمة JSON"
    )

    class Meta:
        verbose_name = "قيمة حقل طلب"
        verbose_name_plural = "قيم حقول الطلبات"
        constraints = [
            models.UniqueConstraint(
                fields=["request", "field"],
                name="uq_request_field_value"
            )
        ]

    def __str__(self):
        return f"{self.request_id} :: {self.field.key}"

    def clean(self):
        # تأكد أن الحقل يتبع لنفس نوع الطلب
        if self.field.request_type_id != self.request.request_type_id:
            raise ValidationError(
                "هذا الحقل لا يتبع لنفس نوع الطلب."
            )

        # تحقق من الإلزامية
        values = [
            self.value_text,
            self.value_number,
            self.value_date,
            self.value_bool,
            self.value_json,
        ]

        if self.field.is_required and not any(v is not None and v != "" for v in values):
            raise ValidationError(
                "هذا الحقل إلزامي ولم يتم إدخال قيمة."
            )
