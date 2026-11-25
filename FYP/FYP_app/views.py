from django.http import FileResponse
from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
import secrets

from rest_framework import generics, status, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth import get_user_model
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
import mimetypes
import uuid

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import (
    User,
    UserProfile,
    Nominee,
    Credentials,
    NomineeRole,
    LegacyAIAccess,
    VaultItem,
    EmailOTP,
)
from .serializers import (
    RegisterSerializer,
    OnboardingSerializer,
    LoginSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    NomineeSerializer,
    CredentialsSerializer,
    NomineeRoleSerializer,
    LegacyAIAccessSerializer,
    TrustedCircleSettingsSerializer,
    VaultItemSerializer,
    SetPasswordSerializer,
)
from .emails import send_otp_email
from .services import send_pending_role_invitations

nominee_signer = TimestampSigner()


def _require_active_legacy_plan(user):
    profile = UserProfile.objects.filter(user=user).first()
    if profile and profile.status != 'active':
        raise PermissionDenied(
            'Legacy assignments are frozen while release verification is active or complete.'
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
            UserProfile.objects.get_or_create(user=user)
            otp = EmailOTP.objects.create(
                user=user,
                otp_code=f'{secrets.randbelow(1_000_000):06d}',
                purpose='register',
            )

        if not send_otp_email(user.email, otp.otp_code, 'register'):
            return Response(
                {
                    'error': 'Account created, but the verification email could not be sent. Request a new code.',
                    'email': user.email,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            "message": "Account created. Check your email for the verification code.",
            "verification_required": True,
            "email": user.email,
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

        if not getattr(user, 'is_active', False):
            raise AuthenticationFailed("Please verify your email before logging in.")

        refresh = RefreshToken.for_user(user)
        profile = getattr(user, 'profile', None)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'onboarding_completed': getattr(profile, 'onboarding_completed', False),
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.get_full_name(),
            },
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

    if not email or not otp_input:
        return Response(
            {'error': 'Email and verification code are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(email=email)
        otp_entry = EmailOTP.objects.filter(user=user, purpose='register').latest('created_at')

        if not otp_entry.is_valid() or otp_entry.otp_code != otp_input:
            return Response(
                {'error': 'Invalid or expired verification code.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            otp_entry.is_used = True
            otp_entry.save(update_fields=['is_used'])
            user.is_active = True
            user.save(update_fields=['is_active'])
            profile, _ = UserProfile.objects.get_or_create(user=user)

        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Email verified successfully.',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'onboarding_completed': profile.onboarding_completed,
        }, status=status.HTTP_200_OK)
    except (User.DoesNotExist, EmailOTP.DoesNotExist):
        return Response(
            {'error': 'Invalid or expired verification code.'},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_registration_otp(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email=email, is_active=False).first()
    if not user:
        return Response(
            {'message': 'If an unverified account exists for this email, a new code has been sent.'},
            status=status.HTTP_200_OK,
        )

    recent_otp = EmailOTP.objects.filter(user=user, purpose='register').order_by('-created_at').first()
    if recent_otp and (timezone.now() - recent_otp.created_at).total_seconds() < 60:
        return Response(
            {'error': 'Please wait before requesting a new verification code.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    otp = EmailOTP.objects.create(
        user=user,
        otp_code=f'{secrets.randbelow(1_000_000):06d}',
        purpose='register',
    )
    if not send_otp_email(user.email, otp.otp_code, 'register'):
        return Response(
            {'error': 'Could not send the verification email. Please try again.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {'message': 'A new verification code has been sent to your email.'},
        status=status.HTTP_200_OK,
    )


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
        otp_string = f'{secrets.randbelow(1_000_000):06d}'
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
    refresh_token = request.data.get("refresh")

    if not refresh_token:
        return Response(
            {"error": "Refresh token is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(
            {"message": "Logged out successfully"},
            status=status.HTTP_200_OK
        )
    except TokenError:
        return Response(
            {"error": "Invalid or expired refresh token"},
            status=status.HTTP_400_BAD_REQUEST
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


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def complete_onboarding(request):
    serializer = OnboardingSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if 'timeout_days' in serializer.validated_data:
        profile.timeout_days = serializer.validated_data['timeout_days']
    profile.onboarding_completed = serializer.validated_data['onboarding_completed']
    profile.save(update_fields=['timeout_days', 'onboarding_completed'])

    return Response({
        'message': 'Onboarding saved successfully.',
        'timeout_days': profile.timeout_days,
        'onboarding_completed': profile.onboarding_completed,
    }, status=status.HTTP_200_OK)


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
    with transaction.atomic():
        profile, _ = UserProfile.objects.select_for_update().get_or_create(
            user=request.user,
        )
        if profile.status == 'released':
            return Response(
                {'error': 'Your legacy has already been released and cannot be relocked.'},
                status=status.HTTP_409_CONFLICT,
            )

        profile.last_seen = timezone.now()
        profile.status = 'active'
        profile.warning_start = None
        profile.release_quorum_snapshot = None
        profile.save(update_fields=[
            'last_seen',
            'status',
            'warning_start',
            'release_quorum_snapshot',
        ])
        witness_roles = NomineeRole.objects.filter(
            nominee__user=request.user,
            role='witness',
        )
        witness_roles.update(
            vote=None,
            voted_at=None,
            verification_sent_at=None,
        )
        for role in witness_roles:
            role.vote_token = uuid.uuid4()
            role.save(update_fields=['vote_token'])

    return Response({
        'message': 'Check-in received. Your vault is active and locked.',
        'last_seen': profile.last_seen,
        'status': profile.status,
        'timeout_days': profile.timeout_days,
    }, status=status.HTTP_200_OK)


# ============================================================
# Nominees
# ============================================================


class NomineeViewSet(viewsets.ModelViewSet):
    serializer_class = NomineeSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Nominee.objects.all()

    def get_queryset(self):
        return Nominee.objects.filter(user=self.request.user).prefetch_related('roles')

    def destroy(self, request, *args, **kwargs):
        nominee = self.get_object()
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile and profile.status != 'active':
            return Response(
                {'error': 'Contacts cannot be removed while release verification is active.'},
                status=status.HTTP_409_CONFLICT,
            )
        if nominee.credentials.exists() or nominee.vault_items.exists():
            return Response(
                {'error': 'Reassign this contact’s credentials and capsules before removing them.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        nominee.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        _require_active_legacy_plan(request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nominee = serializer.save()
        invitations = send_pending_role_invitations(
            nominee,
            request.user.get_full_name() or request.user.email,
        )
        response_data = self.get_serializer(nominee).data
        response_data['invitation_sent'] = invitations['sent']
        response_data['invitations'] = invitations['roles']
        headers = self.get_success_headers(serializer.data)
        return Response(
            response_data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        _require_active_legacy_plan(request.user)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        nominee = serializer.save()
        invitations = send_pending_role_invitations(
            nominee,
            request.user.get_full_name() or request.user.email,
        )
        response_data = self.get_serializer(nominee).data
        response_data['invitation_sent'] = invitations['sent']
        response_data['invitations'] = invitations['roles']
        return Response(response_data)

    @action(detail=True, methods=['post'], url_path='resend-invitation')
    def resend_invitation(self, request, pk=None):
        _require_active_legacy_plan(request.user)
        nominee = self.get_object()
        for role in nominee.roles.filter(consent_status='declined'):
            role.consent_status = 'pending'
            role.confirmed_at = None
            role.invitation_sent_at = None
            role.save(update_fields=[
                'consent_status',
                'confirmed_at',
                'invitation_sent_at',
            ])
        invitations = send_pending_role_invitations(
            nominee,
            request.user.get_full_name() or request.user.email,
            resend=True,
        )
        response_data = self.get_serializer(nominee).data
        response_data['invitation_sent'] = invitations['sent']
        response_data['invitations'] = invitations['roles']
        return Response(response_data)


def _invitation_role_from_token(token):
    try:
        raw_value = nominee_signer.unsign(token, max_age=7 * 24 * 60 * 60)
        role_id, invitation_token, nominee_email = raw_value.split(':', 2)
        invitation_token = uuid.UUID(invitation_token)
        return NomineeRole.objects.select_related(
            'nominee',
            'nominee__user',
        ).get(
            id=role_id,
            invitation_token=invitation_token,
            nominee__nominee_email__iexact=nominee_email,
        )
    except (BadSignature, SignatureExpired, ValueError, NomineeRole.DoesNotExist):
        return None


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def confirm_nominee(request, token):
    role = _invitation_role_from_token(token)
    if role is None:
        return Response({'error': 'This confirmation link is invalid or expired.'}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'GET':
        return Response({
            'nominee_name': role.nominee.nominee_name,
            'owner_name': role.nominee.user.get_full_name() or role.nominee.user.email,
            'role': role.role,
            'role_display': role.get_role_display(),
            'consent_status': role.consent_status,
        })

    decision = request.data.get('decision')
    if decision not in ('accept', 'decline'):
        return Response(
            {'decision': 'Choose accept or decline.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    target_status = 'accepted' if decision == 'accept' else 'declined'
    if role.consent_status != 'pending':
        if role.consent_status == target_status:
            return Response({'consent_status': role.consent_status})
        return Response(
            {'error': 'A different decision has already been recorded.'},
            status=status.HTTP_409_CONFLICT,
        )

    role.consent_status = target_status
    role.confirmed_at = timezone.now() if target_status == 'accepted' else None
    role.save(update_fields=['consent_status', 'confirmed_at'])

    return Response({
        'message': 'Your role decision has been recorded.',
        'consent_status': role.consent_status,
    })


class NomineeRoleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NomineeRoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = NomineeRole.objects.all()  

    def get_queryset(self):
        return NomineeRole.objects.filter(nominee__user=self.request.user)


class LegacyAIAccessViewSet(viewsets.ModelViewSet):
    serializer_class = LegacyAIAccessSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = LegacyAIAccess.objects.all()
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        return LegacyAIAccess.objects.filter(
            user=self.request.user,
        ).select_related('nominee')

    def perform_destroy(self, instance):
        _require_active_legacy_plan(self.request.user)
        instance.delete()

    def create(self, request, *args, **kwargs):
        _require_active_legacy_plan(request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access, created = LegacyAIAccess.objects.get_or_create(
            user=request.user,
            nominee=serializer.validated_data['nominee'],
        )
        response = self.get_serializer(access)
        return Response(
            response.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class TrustedCircleSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _response_data(profile):
        accepted_witnesses = NomineeRole.objects.filter(
            nominee__user=profile.user,
            role='witness',
            consent_status='accepted',
        ).values('nominee_id').distinct().count()
        return {
            'witness_quorum': profile.witness_quorum,
            'accepted_witnesses': accepted_witnesses,
            'ready': accepted_witnesses >= profile.witness_quorum,
            'quorum_frozen': profile.status != 'active',
            'status': profile.status,
        }

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(self._response_data(profile))

    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = TrustedCircleSettingsSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._response_data(profile))

# ============================================================
# Credentials
# ============================================================

class CredentialsListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CredentialsSerializer

    def get_queryset(self):
        return Credentials.objects.filter(user=self.request.user).select_related(
            'user',
            'assigned_nominee',
        )

    def perform_create(self, serializer):
        _require_active_legacy_plan(self.request.user)
        serializer.save(user=self.request.user)


class CredentialsDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CredentialsSerializer

    def get_queryset(self):
        return Credentials.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        _require_active_legacy_plan(self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        _require_active_legacy_plan(self.request.user)
        instance.delete()

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
        _require_active_legacy_plan(self.request.user)
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        _require_active_legacy_plan(self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        _require_active_legacy_plan(self.request.user)
        instance.delete()
############# password setter###########


User = get_user_model()
token_generator = PasswordResetTokenGenerator()

@extend_schema(
    request=SetPasswordSerializer,
    responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
    tags=["Authentication"]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def set_password_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({"error": "Invalid link"}, status=status.HTTP_400_BAD_REQUEST)

    if not token_generator.check_token(user, token):
        return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

    serializer = SetPasswordSerializer(data=request.data)
    if serializer.is_valid():
        user.set_password(serializer.validated_data['password'])
        user.save()
        return Response({"message": "Password set successfully"}, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

###### Release Assets Data####
class MyReleasedAssetsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        nominee = Nominee.objects.filter(
            login_account=request.user,
            roles__role='beneficiary',
            roles__consent_status='accepted',
        ).distinct().first()
        if nominee is None:
            return Response(
                {'error': 'No released beneficiary assets are available for this account.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        vault_items = VaultItem.objects.filter(recipient=nominee, is_sent=True)
        credentials = Credentials.objects.filter(assigned_nominee=nominee, status='released')

        return Response({
            "vault_items": VaultItemSerializer(vault_items, many=True).data,
            "credentials": CredentialsSerializer(credentials, many=True).data,
        })


class MyReleasedCapsuleFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        item = VaultItem.objects.filter(id=pk).select_related('user', 'recipient').first()
        if item is None:
            return Response(
                {'error': 'This capsule is not available to this account.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        owner_profile = UserProfile.objects.filter(user=request.user).first()
        is_owner = (
            item.user_id == request.user.id
            and (owner_profile is None or owner_profile.status != 'released')
        )
        is_released_beneficiary = (
            item.is_sent
            and Nominee.objects.filter(
                id=item.recipient_id,
                login_account=request.user,
                roles__role='beneficiary',
                roles__consent_status='accepted',
            ).exists()
        )
        if not is_owner and not is_released_beneficiary:
            return Response(
                {'error': 'This capsule is not available to this account.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        content_type = mimetypes.guess_type(item.file.name)[0] or 'application/octet-stream'
        return FileResponse(
            item.file.open('rb'),
            as_attachment=True,
            filename=item.file.name.rsplit('/', 1)[-1],
            content_type=content_type,
        )


def home(request):
    return render(request, "FYP_app/Dashboard.html")
