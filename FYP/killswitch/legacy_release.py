import logging
import uuid

from django.db import transaction
from django.utils import timezone

from FYP_app.emails import send_nominee_verification_email
from FYP_app.models import (
    Credentials,
    LegacyAIAccess,
    Nominee,
    NomineeRole,
    UserProfile,
    VaultItem,
)

from .services import send_release_notification_email

logger = logging.getLogger(__name__)


def send_witness_verification_requests(profile):
    owner_name = profile.user.get_full_name() or profile.user.email
    witness_roles = NomineeRole.objects.filter(
        nominee__user=profile.user,
        role='witness',
        consent_status='accepted',
        verification_sent_at__isnull=True,
    ).select_related('nominee')

    for role in witness_roles:
        if send_nominee_verification_email(role, owner_name):
            role.verification_sent_at = timezone.now()
            role.save(update_fields=['verification_sent_at'])


def _release_accepted_beneficiary_assets(profile):
    nominees = Nominee.objects.filter(
        user=profile.user,
        roles__role='beneficiary',
        roles__consent_status='accepted',
    ).distinct()
    release_notifications = []

    for nominee in nominees:
        credentials = Credentials.objects.filter(
            assigned_nominee=nominee,
            status='locked',
        )
        vault_items = VaultItem.objects.filter(
            recipient=nominee,
            is_sent=False,
            release_type='killswitch',
        )
        released_count = credentials.count() + vault_items.count()
        legacy_ai_available = LegacyAIAccess.objects.filter(
            user=profile.user,
            nominee=nominee,
        ).exists()
        credentials.update(status='released')
        vault_items.update(is_sent=True)
        if released_count or legacy_ai_available:
            release_notifications.append((nominee, released_count, legacy_ai_available))

    def notify_beneficiaries():
        for nominee, item_count, legacy_ai_available in release_notifications:
            send_release_notification_email(
                nominee,
                item_count,
                legacy_ai_available=legacy_ai_available,
            )

    transaction.on_commit(notify_beneficiaries)


@transaction.atomic
def record_witness_vote(vote_token, decision):
    if decision not in ('death', 'alive'):
        return {'error': 'Choose death or alive.'}, 400

    role = NomineeRole.objects.select_for_update().filter(
        vote_token=vote_token,
        role='witness',
        consent_status='accepted',
    ).select_related('nominee__user').first()
    if role is None:
        return {'error': 'This witness link is invalid or expired.'}, 404

    profile = UserProfile.objects.select_for_update().filter(
        user=role.nominee.user,
        status='warning',
    ).first()
    if profile is None:
        return {'error': 'There is no active release verification.'}, 400

    if role.vote:
        if role.vote == decision:
            return {
                'message': 'Your vote has already been recorded.',
                'status': profile.status,
                'vote': role.vote,
            }, 200
        return {'error': 'You have already submitted a different vote.'}, 409

    role.vote = decision
    role.voted_at = timezone.now()
    role.save(update_fields=['vote', 'voted_at'])

    quorum = profile.release_quorum_snapshot
    accepted_witnesses = NomineeRole.objects.filter(
        nominee__user=profile.user,
        role='witness',
        consent_status='accepted',
    )
    available_count = accepted_witnesses.values('nominee_id').distinct().count()
    death_votes = accepted_witnesses.filter(vote='death').values('nominee_id').distinct().count()
    alive_votes = accepted_witnesses.filter(vote='alive').values('nominee_id').distinct().count()

    if quorum and available_count >= quorum and death_votes >= quorum:
        profile.status = 'released'
        profile.released_at = timezone.now()
        profile.save(update_fields=['status', 'released_at'])
        _release_accepted_beneficiary_assets(profile)
    elif quorum and available_count >= quorum and alive_votes >= quorum:
        profile.status = 'active'
        profile.last_seen = timezone.now()
        profile.warning_start = None
        profile.release_quorum_snapshot = None
        profile.save(update_fields=[
            'status',
            'last_seen',
            'warning_start',
            'release_quorum_snapshot',
        ])
        accepted_witnesses.update(vote=None, voted_at=None, verification_sent_at=None)
        for witness_role in accepted_witnesses:
            witness_role.vote_token = uuid.uuid4()
            witness_role.save(update_fields=['vote_token'])

    return {
        'message': 'Your vote has been recorded.',
        'status': profile.status,
        'death_votes': death_votes,
        'alive_votes': alive_votes,
        'required_witnesses': quorum,
        'eligible_witnesses': available_count,
    }, 200
