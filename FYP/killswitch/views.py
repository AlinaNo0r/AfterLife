from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from FYP_app.models import Nominee, NomineeRole

from .legacy_release import record_witness_vote


def _vote_response(token, decision):
    data, status_code = record_witness_vote(token, decision)
    return Response(data, status=status_code)


@api_view(['POST'])
@permission_classes([AllowAny])
def vote_death(request, token):
    return _vote_response(token, 'death')


@api_view(['POST'])
@permission_classes([AllowAny])
def vote_alive(request, token):
    return _vote_response(token, 'alive')


class NomineeConfirmDeathView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        nominee = Nominee.objects.filter(login_account=request.user).first()
        if nominee is None:
            return Response(
                {'error': 'This account is not linked to a trusted contact.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        role = NomineeRole.objects.filter(
            nominee=nominee,
            role='witness',
            consent_status='accepted',
        ).first()
        if role is None:
            return Response(
                {'error': 'You have not accepted the death witness role.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        decision = request.data.get('decision')
        return _vote_response(role.vote_token, decision)
