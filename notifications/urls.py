from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='list'), # صفحة الإشعارات
    path('read/<int:notif_id>/', views.mark_read_and_redirect, name='mark_read'),
    path('mark-all-read/', views.mark_all_as_read, name='mark_all_read'), # زر تحديد الكل
]