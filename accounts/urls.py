from django.contrib.auth import views as auth_views
from django.urls import path
from .views import (
    login_view,
    client_dashboard,
    vendor_dashboard,
    logout_view,
)


urlpatterns = [
    
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    path('client/dashboard/', client_dashboard, name='client_dashboard'),
    path('vendor/dashboard/', vendor_dashboard, name='vendor_dashboard'),

]