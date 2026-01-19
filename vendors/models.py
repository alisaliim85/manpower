from django.db import models
from accounts.models import Company


class Vendor(models.Model):
    """
    شركة توريد العمالة
    مرتبطة بجهة من نوع (vendor) في accounts
    """

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        limit_choices_to={'company_type': 'vendor'},
        related_name='vendor_profile',
        verbose_name='شركة التوريد'
    )

    contact_name = models.CharField(
        max_length=255,
        verbose_name='اسم مسؤول التواصل'
    )

    contact_phone = models.CharField(
        max_length=20,
        verbose_name='رقم التواصل'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='نشطة'
    )
    clients = models.ManyToManyField(Company,related_name='contracted_vendors',limit_choices_to={'company_type': 'client'},verbose_name='العملاء المتعاقد معهم',blank=True)

    @property
    def get_all_staff(self):
        """
        جلب جميع المستخدمين المرتبطين بشركة التوريد هذه.
        يعتمد على العلاقة العكسية من مودل Company إلى User.
        """
        # عادة العلاقة العكسية تكون user_set إلا إذا قمت بتغيير related_name في مودل User
        if hasattr(self.company, 'users'): 
            return self.company.users.all()
        elif hasattr(self.company, 'user_set'):
            return self.company.user_set.all()
        return []

    def __str__(self):
        return self.company.name



class Worker(models.Model):
    """
    العامل التابع لشركة توريد
    """

    STATUS_CHOICES = (
        ('active', 'على رأس العمل'),
        ('vacation', 'إجازة'),
        ('exit_final', 'خروج نهائي'),
        ('terminated', 'منتهي التعاقد'),
    )

    INSURANCE_CLASS_CHOICES = (
        ('vip', 'VIP'),
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
    )

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='workers',
        verbose_name='شركة التوريد'
    )

    full_name = models.CharField(
        max_length=255,
        verbose_name='اسم العامل'
    )

    iqama_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='رقم الإقامة'
    )

    nationality = models.CharField(
        max_length=100,
        verbose_name='الجنسية'
    )

    job_title = models.CharField(
        max_length=100,
        verbose_name='المسمى الوظيفي'
    )

    insurance_class = models.CharField(
        max_length=10,
        choices=INSURANCE_CLASS_CHOICES,
        verbose_name='فئة التأمين'
    )

    iqama_expiry_date = models.DateField(
        verbose_name='تاريخ انتهاء الإقامة'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='حالة العامل'
    )

    joined_at = models.DateField(
        verbose_name='تاريخ المباشرة'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإضافة'
    )

    def __str__(self):
        return f"{self.full_name} - {self.iqama_number}"
