from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from FYP_app.models import UserProfile, Nominee, NomineeRole
from rest_framework.permissions import AllowAny, IsAuthenticated
from .services import release_assets_for_single_nominee, release_assets


def _tally_and_apply(profile):
    """Witness votes count karo, majority decide karo."""
    witness_roles = NomineeRole.objects.filter(nominee__user=profile.user, role='witness')
    total = witness_roles.count()
    death_votes = witness_roles.filter(vote='death').count()
    alive_votes = witness_roles.filter(vote='alive').count()

    if total == 0:
        return

    if death_votes > total / 2:
        profile.status = 'released'
        profile.save()
        release_assets(profile)
    elif alive_votes > total / 2:
        profile.status = 'active'
        profile.last_seen = timezone.now()
        profile.warning_start = None
        profile.save()


@api_view(['POST'])
@permission_classes([AllowAny])
def vote_death(request, token):
    role = NomineeRole.objects.filter(vote_token=token, role='witness').first()
    if not role:
        return Response({"error": "Invalid or expired link."}, status=404)

    profile = UserProfile.objects.filter(user=role.nominee.user, status='warning').first()
    if not profile:
        return Response({"error": "No pending warning for this user."}, status=400)

    role.vote = 'death'
    role.confirmed_at = timezone.now()
    role.save()

    _tally_and_apply(profile)
    return Response({"message": "Your vote (death confirmed) has been recorded."})


@api_view(['POST'])
@permission_classes([AllowAny])
def vote_alive(request, token):
    role = NomineeRole.objects.filter(vote_token=token, role='witness').first()
    if not role:
        return Response({"error": "Invalid or expired link."}, status=404)

    profile = UserProfile.objects.filter(user=role.nominee.user, status='warning').first()
    if not profile:
        return Response({"error": "No pending warning for this user."}, status=400)

    role.vote = 'alive'
    role.confirmed_at = timezone.now()
    role.save()

    _tally_and_apply(profile)
    return Response({"message": "Your vote (user is alive) has been recorded."})


class NomineeConfirmDeathView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            nominee = Nominee.objects.get(login_account=request.user)
        except Nominee.DoesNotExist:
            return Response({"error": "This account is not linked to a nominee."}, status=404)

        profile = UserProfile.objects.filter(user=nominee.user, status='fallback').first()
        if not profile:
            return Response({"error": "No pending confirmation available for this account."}, status=400)

        role = nominee.roles.filter(role='beneficiary').first()
        if not role:
            return Response({"error": "You are not a beneficiary for this account."}, status=403)

        role.confirmed_at = timezone.now()
        role.save()

        release_assets_for_single_nominee(nominee)

        return Response({"message": "Death confirmed. Your assigned assets have been released to you."})