from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from accounts.views import landing_page

urlpatterns = [
    

    path('', landing_page, name='landing'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('vendors/', include('vendors.urls')),
    path('requests/', include('requests.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
