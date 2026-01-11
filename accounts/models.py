from django.contrib.auth.models import AbstractUser
from django.db import models


class Company(models.Model):
    """
    تمثل الجهة:
    - شركة العميل
    - شركة توريد عمالة
    """

    COMPANY_TYPE_CHOICES = (
        ('client', 'شركة العميل'),
        ('vendor', 'شركة توريد'),
    )

    name = models.CharField(
        max_length=100,
        verbose_name='اسم الجهة'
    )

    company_type = models.CharField(
        max_length=20,
        choices=COMPANY_TYPE_CHOICES,
        verbose_name='نوع الجهة'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='نشطة'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )

    def __str__(self):
        return self.name


class Role(models.Model):
    """
    الدور الوظيفي داخل النظام
    مثال:
    - موظف مكتب
    - موظف شركة توريد
    - مدير
    """

    name = models.CharField(
        max_length=100,
        verbose_name='اسم الدور'
    )

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='الكود'
    )
    VERBOSE_NAME = 'الدور الوظيفي'
    VERBOSE_NAME_PLURAL = 'الأدوار الوظيفية'
    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    المستخدم المخصص للنظام
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='الجهة'
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='الدور الوظيفي'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط'
    )
    VERBOSE_NAME = 'المستخدم'
    VERBOSE_NAME_PLURAL = 'المستخدمون'
    def __str__(self):
        return self.get_full_name() or self.username
