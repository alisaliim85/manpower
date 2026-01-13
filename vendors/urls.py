from django.urls import path
from .views import vendor_detail_view, VendorCreateView

app_name = 'vendors'

urlpatterns = [
    # الرابط الحقيقي الآن مرتبط بالـ View البرمجي
    path('<int:pk>/detail/', vendor_detail_view, name='vendor_detail'),
    path('create/', VendorCreateView.as_view(), name='vendor_create'),
]