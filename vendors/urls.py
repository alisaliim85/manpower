from django.urls import path
from .views import vendor_detail_view, VendorCreateView, VendorListView, WorkerListView, WorkerDetailView

app_name = 'vendors'

urlpatterns = [
    # الرابط الحقيقي الآن مرتبط بالـ View البرمجي
    path('<int:pk>/detail/', vendor_detail_view, name='vendor_detail'),
    path('create/', VendorCreateView.as_view(), name='vendor_create'),
    # رابط قائمة الشركات
    path('list/', VendorListView.as_view(), name='vendor_list'),
    path('workers/', WorkerListView.as_view(), name='worker_list'),
    path('workers/<int:pk>/', WorkerDetailView.as_view(), name='worker_detail'),
]