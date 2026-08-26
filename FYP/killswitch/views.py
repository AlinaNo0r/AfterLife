from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from FYP_app.models import UserProfile
from rest_framework.permissions import AllowAny


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_witness(request, token):
    profile = UserProfile.objects.filter(witness_token=token, status='warning').first()

    if not profile:
        return Response(
            {"error": "Invalid or expired confirmation link."}, 
            status=404
        )

    profile.witness_confirmed = True
    profile.witness_response_at = timezone.now()
    profile.save()

    return Response({"message": "Confirmation received. Assets will be released shortly."})
