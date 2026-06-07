from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Nominee, Credentials, User, UserProfile
from .serializers import NomineeSerializer, CredentialsSerializer, UserSerializer, ChangePasswordSerializer
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone


@api_view(['POST'])
def stay_alive(request):
    profile, created = UserProfile.objects.get_or_create(
        user=request.user
    )
    
    profile.last_seen = timezone.now()
    profile.status = 'active'
    profile.warning_start = None
    
    profile.save()
    
    return Response({
        'message': 'Signal received! Your status is now active.',
        'last_seen': profile.last_seen,
        'status': profile.status,
    }, status=status.HTTP_200_OK)


class change_password(APIView):
    permission_classes = []

    def put(self, request):
        try:
            user = request.user
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request, 'user': user}  # ← user bhi pass karo
        )
        
        if serializer.is_valid():
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response(
                {"message": "Password updated successfully."},
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserDetailView(generics.RetrieveAPIView):
    def get(self, request):
       user = request.user
       serializer = UserSerializer(user)
       return Response(serializer.data)

@api_view(['PATCH'])
def edit_user(request):
    user = request.user
    allowed_fields = ['first_name', 'last_name', 'email', 'dob', 'gender', 'phone']
    
    for field in allowed_fields:
        if field in request.data:
            setattr(user, field, request.data[field])
    
    user.save()  
    
    return Response({
        'message': 'User updated successfully',
        'data': {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'dob': user.dob,
            'gender': user.gender,
            'phone': user.phone,
        }
    }, status=status.HTTP_200_OK)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')

    user = authenticate(request, username=email, password=password)

    if user is not None:
        login(request, user)
        return Response({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name()
            }
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': 'Invalid username or password'
        }, status=status.HTTP_401_UNAUTHORIZED)


def home(request):
    return render(request, 'FYP_app/Dashboard.html')

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    full_name = request.data.get('full_name')
    email = request.data.get('email')
    password = request.data.get('password')
    dob = request.data.get('dob')
    gender = request.data.get('gender')
    phone = request.data.get('phone')
    
    required_fields = ['full_name', 'email', 'password', 'phone']
    for field in required_fields:
        if not request.data.get(field):
            return Response({
                'error': f'{field} is required'
            }, status=status.HTTP_400_BAD_REQUEST)
    

    # check if email already exists
    if User.objects.filter(email=email).exists():
        return Response({
            'error': 'An account with this email already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    
    # split full name
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    
    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        dob=dob,
        gender=gender,
        phone=phone
    )

    return Response({
        'message': 'Account created successfully',
        'user': {
            'id': user.id,
            'email': user.email,
            'full_name': user.get_full_name(),
            'gender': user.gender
        }
    }, status=status.HTTP_201_CREATED)



@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({
        'message': 'Logged out successfully'
    }, status=status.HTTP_200_OK)

@csrf_exempt
@api_view(['DELETE'])
def delete_user(request):
    try:
        user = request.user
        user.delete()
        return Response(
            {'message': 'User deleted successfully'},
            status=status.HTTP_200_OK
        )
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
class NomineeListView(generics.ListCreateAPIView):
    serializer_class = NomineeSerializer

    def perform_create(self, serializer):
      serializer.save(user=self.request.user)

    def get_queryset(self):
        return Nominee.objects.filter(user=self.request.user)

class NomineeDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NomineeSerializer
    

    def get_queryset(self):
        return Nominee.objects.filter(user=self.request.user)

class CredentialsListView(generics.ListCreateAPIView):
    serializer_class = CredentialsSerializer

    def perform_create(self, serializer):
      serializer.save(user=self.request.user)

    def get_queryset(self):
        return Credentials.objects.filter(user=self.request.user)
    
class CredentialsDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CredentialsSerializer
    def get_queryset(self):
      return Credentials.objects.filter(user=self.request.user)