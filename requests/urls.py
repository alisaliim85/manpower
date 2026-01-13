from django.urls import path
from . import views

app_name = 'requests'

urlpatterns = [
    # 1. رابط قائمة الطلبات (الصفحة الرئيسية للتطبيق)
    # الوصول إليه عبر: {% url 'requests:list' %}
    path('', views.RequestListView.as_view(), name='list'),
    
    # 2. رابط الـ Wizard لإنشاء طلب جديد
    # الوصول إليه عبر: {% url 'requests:create_wizard' %}
    path('new/', views.RequestWizardView.as_view(), name='create_wizard'),
    
    # 3. رابط الـ API لجلب الحقول ديناميكياً (يستخدم بواسطة JavaScript فقط)
    path('api/get-fields/<int:type_id>/', views.get_request_fields, name='get_fields'),
    
    # 4. رابط تفاصيل طلب معين (سنحتاجه لاحقاً)
    path('<int:pk>/', views.RequestDetailView.as_view(), name='detail'),
]