
from django.urls import path
from .views import confirm_witness


urlpatterns = [
    path('api/confirm-witness/<uuid:token>/', confirm_witness, name='confirm-witness'),
]