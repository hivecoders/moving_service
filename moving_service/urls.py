from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from users import views
urlpatterns = [
    path('dashboard/customer/', views.customer_dashboard, name='customer_dashboard'),
    path('dashboard/mover/', views.mover_dashboard, name='mover_dashboard'),
]
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  #login, logout
    path('users/', include('users.urls')),  # ueers app
    path('', views.home, name='home'),  # home page
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

#media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
