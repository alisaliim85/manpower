from django.db import models
from django.conf import settings
from requests.models import Request 

class Notification(models.Model):
    recipient = models.ForeignKey(
            settings.AUTH_USER_MODEL, 
            on_delete=models.CASCADE, 
            related_name='notifications', 
            verbose_name="المستقبل"
        )
    request = models.ForeignKey(
            Request, 
            on_delete=models.CASCADE, 
            null=True, 
            blank=True, 
            verbose_name="الطلب المرتبط"
        )
    title = models.CharField(max_length=40, verbose_name="العنوان")
    message = models.TextField(verbose_name="الرسالة")
    is_read = models.BooleanField(default=False, verbose_name="تمت القراءة")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
            ordering = ['-created_at']

    def __str__(self):
            return f"تنبيه لـ {self.recipient} - {self.title}"