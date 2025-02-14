from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from users import views  

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'), 
    path('users/', include('users.urls')),  
    path('accounts/', include('django.contrib.auth.urls')),  
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)