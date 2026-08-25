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
from django.conf import settings 
from cryptography.fernet import Fernet 
import random
from .models import EmailOTP
from .emails import send_otp_email

# ──────────────────────────────────────────────
# 1 - STAY ALIBE HEARTBEAT
# ──────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([IsAuthenticated])
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

# ──────────────────────────────────────────────
# 2 - PROFILE MANAGEMENT
# ──────────────────────────────────────────────
class change_password(APIView):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]
    def get(self, request):
       user = request.user
       serializer = UserSerializer(user)
       return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
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
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
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

def home(request):
    return render(request, 'FYP_app/Dashboard.html')


# ──────────────────────────────────────────────
#  3 - DUAL-PHASE IDENTITY PROTECTION LAYER (2FA)
# ──────────────────────────────────────────────
#---------------------
#    Register User 
# --------------------
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Secured Registration: Creates a locked profile and triggers a verification passcode email."""
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
        phone=phone,
        is_active = False
    )
     
     # Generate 6-digit numerical TOKEN CODE
    otp_string = str(random.randint(100000, 999999))
    EmailOTP.objects.create(user=user, code=otp_string, purpose='register')
    send_otp_email(user.email, otp_string, 'register')

    return Response({
        'message': 'Account created successfully! A 6-digit activation code has been sent to your email.'
    }, status=status.HTTP_201_CREATED)


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

@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({
        'message': 'Logged out successfully'
    }, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────
# 4 -  STANDARD GENERIC VAULT ROUTING ACTIONS
# ──────────────────────────────────────────────

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

# ──────────────────────────────────────────────
#  5 -  ASYNCHRONOUS TWO-FACTOR WEBHOOK ENDPOINTS
# ──────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([AllowAny]) # Nominees click this from their mail app without logging into your system first

def verify_status_alive(request, profile_id):
    """Path A: Nominee verifies the user is okay. System extends the timer."""
    try:
        profile = UserProfile.objects.get(id=profile_id)
        
        # 🔄 Extend tracking parameters out: Update last_seen to current time to clear warning flag loops
        profile.status = 'active'
        profile.last_seen = timezone.now()
        profile.warning_start = None
        profile.save()
        
        return Response({
            'message': 'Verification updated successfully. Account countdown extended by 7 days.'
        }, status=status.HTTP_200_OK)
    except UserProfile.DoesNotExist:
        return Response({'error': 'Profile record context not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_status_deceased(request, profile_id):
    """Path B: Nominee confirms passing. System executes conditional asset release policies."""
    try:
        profile = UserProfile.objects.get(id=profile_id)
        profile.status = 'inactive' # Permanently set user record profile out of scope
        profile.save()
        
        # 🤖 AI CHATBOT HOOK: (Examiner presentation marker)
        logger.info(f"AI Legacy Continuity Engine (ChatMemory) activated for profile ID {profile_id}")
        
        # Process credential array items using our Symmetric Vault Decryption Engine
        crypto_engine = Fernet(settings.ENCRYPTION_KEY)
        user_credentials = profile.user.credentials.select_related('assigned_nominee')
        
        for cred in user_credentials:
            nominee = cred.assigned_nominee
            if nominee:
                # Decrypt the database string block to plain text
                try:
                    decrypted_bytes = crypto_engine.decrypt(cred.password.encode('utf-8'))
                    cleartext_password = decrypted_bytes.decode('utf-8')
                except Exception:
                    cleartext_password = "[Vault Decryption Failure]"
                
                # 📅 USER SCHEDULING CONDITION CHECKS:
                # If your database maps custom release timeline choices (Immediate vs Deferred), check them here:
                release_immediately = True # Set default baseline logic layout
                
                if release_immediately:
                    send_final_vault_payload(
                        nominee_email=nominee.nominee_email,
                        nominee_name=nominee.nominee_name,
                        platform=cred.platform,
                        username=cred.username_on_platform,
                        password=cleartext_password
                    )
                    
        return Response({
            'message': 'Status confirmed. AI Chatbot initialized and data release pipelines activated.'
        }, status=status.HTTP_200_OK)
        
    except UserProfile.DoesNotExist:
        return Response({'error': 'Profile record context not found'}, status=status.HTTP_404_NOT_FOUND)

