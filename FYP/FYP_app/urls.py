from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter
from .views import NomineeRoleViewSet, NomineeViewSet, VaultItemViewSet

router = DefaultRouter()
router.register('nominee-roles', NomineeRoleViewSet, basename='nominee-role')
router.register('nominees', NomineeViewSet, basename='nominee')
router.register('vault-items', VaultItemViewSet, basename='vault-item')


urlpatterns = [
    # Auth
    path('api/register/', views.register_view, name='register'),
    path('api/login/', views.LoginView.as_view(), name='login'),
    path('api/logout/', views.logout_view, name='logout'),
    
    # User
    path('api/user/', views.UserDetailView.as_view(), name='user-detail'),
    path('api/user/edit/', views.edit_user, name='edit-user'),
    path('api/user/delete/', views.delete_user, name='delete-user'),
    path('api/user/change-password/', views.ChangePasswordView.as_view, name='change-password'),
    
    # Credentials
    path('api/credentials/', views.CredentialsListView.as_view(), name='credentials'),
    path('api/credentials/<int:pk>/', views.CredentialsDetailView.as_view(), name='credential-detail'),
    
    # StayAlive
    path('api/stay-alive/', views.stay_alive, name='stay-alive'),


]
urlpatterns += router.urls
