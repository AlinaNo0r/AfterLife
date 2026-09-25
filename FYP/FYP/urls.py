from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from FYP_app import views
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Main app APIs
    path('', include('FYP_app.urls')),

    # Killswitch APIs
    path('api/killswitch/', include('killswitch.urls')),

    # Swagger / OpenAPI (drf-spectacular)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Media files (vault uploads) — development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)