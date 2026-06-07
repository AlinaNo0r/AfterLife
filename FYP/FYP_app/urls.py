from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('api/register/', views.register_view, name='register'),
    path('api/login/', views.login_view, name='login'),
    path('api/logout/', views.logout_view, name='logout'),
    
    # User
    path('api/user/', views.UserDetailView.as_view(), name='user-detail'),
    path('api/user/edit/', views.edit_user, name='edit-user'),
    path('api/user/delete/', views.delete_user, name='delete-user'),
    path('api/user/change-password/', views.change_password.as_view(), name='change-password'),
    
    # Nominees
    path('api/nominees/', views.NomineeListView.as_view(), name='nominees'),
    path('api/nominees/<int:pk>/', views.NomineeDetailView.as_view(), name='nominee-detail'),
    
    # Credentials
    path('api/credentials/', views.CredentialsListView.as_view(), name='credentials'),
    path('api/credentials/<int:pk>/', views.CredentialsDetailView.as_view(), name='credential-detail'),
    
    # StayAlive
    path('api/stay-alive/', views.stay_alive, name='stay-alive'),


]