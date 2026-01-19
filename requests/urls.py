from django.urls import path
from . import views

app_name = 'requests'

urlpatterns = [

    path('', views.request_list, name='list'),
    
    path('new/', views.create_request_wizard, name='create_wizard'),    
    path('api/get-fields/<int:type_id>/', views.get_request_fields, name='get_fields'),
    
    
    # 4. رابط تفاصيل طلب معين (سنحتاجه لاحقاً)
    path('<int:pk>/', views.request_detail, name='detail'),
]