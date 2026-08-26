from django.contrib import admin
from django.urls import path, include
from FYP_app import views
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="Afterlife Digital Vault API",
      default_version='v1',
      description="Secured Backend Layer with Symmetric Encryption, MFA, and Automated Killswitch Hooks",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('home', views.home, name='home'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('FYP_app/', include("FYP_app.urls"))
]
    path('', include("FYP_app.urls")),
    path('api/killswitch/', include('killswitch.urls')),


    # ======================
    # Swagger / OpenAPI Docs
    # ======================
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
