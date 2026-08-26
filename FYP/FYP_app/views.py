from django.shortcuts import render
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import transaction

from rest_framework import generics, status, viewsets, permissions, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError, NotFound, AuthenticationFailed
from rest_framework.parsers import MultiPartParser, FormParser

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import User, UserProfile, Nominee, Credentials, NomineeRole, VaultItem
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    NomineeSerializer,
    CredentialsSerializer,
    NomineeRoleSerializer,
    VaultItemSerializer
)


# ============================================================
# Authentication
# ============================================================

@extend_schema(
    request=RegisterSerializer,
    responses={201: OpenApiResponse(description="User registered successfully")},
    tags=["Authentication"]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            user = serializer.save()
            UserProfile.objects.create(user=user)

        return Response({
            "message": "Account created successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.get_full_name(),
                "gender": user.gender,
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {"error": "Registration failed", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: dict},
        tags=["Authentication"]
    )
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(username=email, password=password)

        if not user:
            raise AuthenticationFailed("Invalid email or password")

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.get_full_name(),
            }
        }, status=status.HTTP_200_OK)

# --------------------------------
# verify registration through otp
# --------------------------------
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_registration_otp(request):
    """Validates registration passcode and activates the locked account profile."""
    email = request.data.get('email')
    otp_input = request.data.get('otp')

    try:
        user = User.objects.get(email=email)
        otp_entry = EmailOTP.objects.filter(user=user, purpose='register').latest('created_at')

        if otp_entry.is_valid() and otp_entry.otp_code == otp_input:
            otp_entry.is_used = True
            otp_entry.save()

            user.is_active = True
            user.save()
            return Respose({'Message': 'Profile activation successful! You can now log in.'}, status=status.HTTPS_200_OK)
    
    except(User.DoesNotExist, EmailOTP.DoesNotExist):
        return Response({'error': 'Invalid or expired activation passcode'}, status=status.HTTP_400_BAD_REQUEST)


# ----------------
#   Login User
# ----------------

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Secured Login Phase 1: Validates matching credentials and steps back to trigger a 2FA email challenge."""
    email = request.data.get('email')
    password = request.data.get('password')

    user = authenticate(request, username=email, password=password)

    if user is not None:
        # Generate a fresh time-sensitive login verification passcode
        otp_string = str(random.randint(100000, 999999))
        EmailOTP.objects.create(user=user, otp_code=otp_string, purpose='login')
        send_otp_email(user.email, otp_string, 'login')

        return Response({
            'message': 'Credentials verified successfully. Step 2 MFA token dispatched to your email.'
        }, status=status.HTTP_200_OK)

    else:
        return Response({'error': 'Invalid email username or account password credentials'}, status=status.HTTP_401_UNAUTHORIZED)


# -------------------------------
# Verification using OTP
# -------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_login_otp(request):
    """Secured Login Phase 2: Validates the 2FA passcode and safely signs the user into their session dashboard."""
    
    email = request.data.get('email')
    otp_input = request.data.get('otp')
    
    try:
        user = User.objects.get(email=email)
        otp_entry = EmailOTP.objects.filter(user=user, purpose='login').latest('created_at')
        
        if otp_entry.is_valid() and otp_entry.otp_code == otp_input:
            otp_entry.is_used = True
            otp_entry.save()
            
            # 🔓 Log the authenticated user session into application dashboard state
            login(request, user)
            return Response({
                'message': '2FA verification cleared. Login successful.',
                'user': {'id': user.id, 'email': user.email, 'full_name': f"{user.first_name} {user.last_name}"}
            }, status=status.HTTP_200_OK)
            
        return Response({'error': 'Invalid or expired 2FA passcode entry token'}, status=status.HTTP_400_BAD_REQUEST)
    except (User.DoesNotExist, EmailOTP.DoesNotExist):
        return Response({'error': 'Authentication context parameters missing'}, status=status.HTTP_404_NOT_FOUND)

# --------------
#      LOGOUT 
# --------------

@extend_schema(tags=["Authentication"])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        request.user.auth_token.delete()
        return Response(
            {"message": "Logged out successfully"},
            status=status.HTTP_200_OK
        )
    except Exception:
        return Response(
            {"error": "Logout failed"},
            status=status.HTTP_400_BAD_REQUEST
        )


# ============================================================
# User
# ============================================================

class UserDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


@extend_schema(
    request=UserSerializer,
    responses={200: UserSerializer},
    tags=["User"]
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def edit_user(request):
    user = request.user
    allowed_fields = ['first_name', 'last_name', 'email', 'dob', 'gender', 'phone']

    data = {field: request.data[field] for field in allowed_fields if field in request.data}

    if not data:
        return Response(
            {"error": "No valid fields provided"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if email is being changed and already exists
    if "email" in data and User.objects.filter(email=data["email"]).exclude(id=user.id).exists():
        return Response(
            {"error": "Email already in use"},
            status=status.HTTP_400_BAD_REQUEST
        )

    for field, value in data.items():
        setattr(user, field, value)

    try:
        user.save()
        return Response({
            "message": "User updated successfully",
            "data": UserSerializer(user).data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": "Update failed", "detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: OpenApiResponse(description="Password changed successfully")},
        tags=["User"]
    )
    def put(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        # Force re-login
        Token.objects.filter(user=user).delete()

        return Response(
            {"message": "Password updated successfully. Please login again."},
            status=status.HTTP_200_OK
        )


@extend_schema(tags=["User"])
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user(request):
    try:
        user = request.user
        user.delete()
        return Response(
            {"message": "User deleted successfully"},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"error": "Failed to delete user", "detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


# ============================================================
# Heartbeat / Stay Alive
# ============================================================

@extend_schema(tags=["Heartbeat"])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stay_alive(request):
   try:
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    profile.last_seen = timezone.now()
    profile.status = 'active'
    profile.warning_start = None
    profile.released_at = None
    profile.save()
    
    return Response({
        'message': 'Heartbeat received. Status is now active.',
        'last_seen': profile.last_seen,
        'status': profile.status,
        'timeout_days': profile.timeout_days
    }, status=status.HTTP_200_OK)

   except Exception as e:
        return Response(
            {"error": "Failed to update status", "detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


# ============================================================
# Nominees
# ============================================================


class NomineeViewSet(viewsets.ModelViewSet):

    serializer_class = NomineeSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Nominee.objects.all()  

    def get_queryset(self):
        return Nominee.objects.filter(user=self.request.user)


class NomineeRoleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NomineeRoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = NomineeRole.objects.all()  

    def get_queryset(self):
        
        return NomineeRole.objects.filter(nominee__user=self.request.user)

# ============================================================
# Credentials
# ============================================================

class CredentialsListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CredentialsSerializer

    def get_queryset(self):
        return Credentials.objects.filter(user=self.request.user).select_related("user")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CredentialsDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CredentialsSerializer

    def get_queryset(self):
        return Credentials.objects.filter(user=self.request.user)


# ============================================================
# Vault item
# ============================================================
class VaultItemViewSet(viewsets.ModelViewSet):
    serializer_class = VaultItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = VaultItem.objects.all()
    parser_classes = [MultiPartParser, FormParser]


    def get_queryset(self):
        return VaultItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)




def home(request):
    return render(request, "FYP_app/Dashboard.html")
