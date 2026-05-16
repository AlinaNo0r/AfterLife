from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view

# Create your views here.
def home(request):
    return render(request, 'FYP_app/Dashboard.html')
