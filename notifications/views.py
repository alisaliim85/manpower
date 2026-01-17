from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from .models import Notification

@login_required
def mark_read_and_redirect(request, notif_id):
    # جلب التنبيه والتأكد أنه يخص المستخدم الحالي
    notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    
    # تحديث الحالة لمقروء
    if not notif.is_read:
        notif.is_read = True
        notif.save()
    
    # التوجيه لصفحة تفاصيل الطلب إذا وجد، وإلا للرئيسية
    if notif.request:
        return redirect('requests:detail', pk=notif.request.id)
    else:
        return redirect('landing') # أو dashboard حسب الرابط الرئيسي لديك


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications-templates/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 10  # عدد الإشعارات في الصفحة الواحدة

    def get_queryset(self):
        # 1. جلب إشعارات المستخدم الحالي فقط
        qs = Notification.objects.filter(recipient=self.request.user)

        # 2. منطق البحث (Search)
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(title__icontains=query) | 
                Q(message__icontains=query)
            )

        # 3. منطق الفلترة (Filter)
        filter_status = self.request.GET.get('filter')
        if filter_status == 'read':
            qs = qs.filter(is_read=True)
        elif filter_status == 'unread':
            qs = qs.filter(is_read=False)

        return qs

    def post(self, request, *args, **kwargs):
        # هذا الجزء خاص بزر "تحديد الكل كمقروء"
        if 'mark_all_read' in request.path:
            Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
            return redirect('notifications:list')
        return super().get(request, *args, **kwargs)

# دالة لتحديد الكل كمقروء (رابط منفصل)
def mark_all_as_read(request):
    if request.user.is_authenticated:
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect('notifications:list')