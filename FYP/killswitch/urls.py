
from django.urls import path
from .views import vote_death, vote_alive, NomineeConfirmDeathView


urlpatterns = [
    path('confirm-death/', NomineeConfirmDeathView.as_view(), name='confirm-death'),
    path('vote-death/<uuid:token>/', vote_death, name='vote-death'),
    path('vote-alive/<uuid:token>/', vote_alive, name='vote-alive'),
]