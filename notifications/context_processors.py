from .models import Notification

def notifications_processor(request):
    # التأكد من أن المستخدم مسجل دخول
    if request.user.is_authenticated:
        # جلب التنبيهات غير المقروءة (للعداد الأحمر)
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        
        # جلب آخر 5 تنبيهات للقائمة المنسدلة
        recent_notifications = Notification.objects.filter(recipient=request.user)[:5]
        
        return {
            'unread_count': unread_count,
            'recent_notifications': recent_notifications
        }
    return {}