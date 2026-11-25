import logging
import os
import uuid

from apscheduler.schedulers.background import BackgroundScheduler
from django.db import transaction
from django.utils import timezone

from FYP_app.emails import send_legacy_warning_email
from FYP_app.models import NomineeRole, UserProfile

from .legacy_release import send_witness_verification_requests
from .services import check_scheduled_releases

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def check_all_heartbeats():
    now = timezone.now()
    profile_ids = UserProfile.objects.filter(
        status__in=['active', 'warning'],
    ).values_list('id', flat=True)

    for profile_id in profile_ids:
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().select_related(
                'user',
            ).filter(id=profile_id).first()
            if profile is None:
                continue

            if profile.status == 'active':
                inactive_days = (now - profile.last_seen).days
                if inactive_days < profile.timeout_days:
                    continue

                profile.status = 'warning'
                profile.warning_start = now
                profile.release_quorum_snapshot = profile.witness_quorum
                profile.save(update_fields=[
                    'status',
                    'warning_start',
                    'release_quorum_snapshot',
                ])
                witness_roles = NomineeRole.objects.filter(
                    nominee__user=profile.user,
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

                transaction.on_commit(
                    lambda email=profile.user.email, name=(
                        profile.user.get_full_name() or profile.user.username
                    ), days=inactive_days: send_legacy_warning_email(
                        email,
                        name,
                        days,
                    )
                )
                logger.warning(
                    "User profile %s entered warning; witness quorum frozen at %s",
                    profile.id,
                    profile.release_quorum_snapshot,
                )
                continue

            if profile.warning_start is None:
                logger.error(
                    "Warning profile %s has no warning_start; leaving assets locked",
                    profile.id,
                )
                continue

            if (now - profile.warning_start).days >= 7:
                transaction.on_commit(
                    lambda current_profile=profile: send_witness_verification_requests(
                        current_profile
                    )
                )


def start_scheduler():
    if scheduler.running:
        logger.info("Killswitch scheduler already running")
        return
    if os.environ.get('RUN_MAIN') != 'true':
        return

    scheduler.add_job(
        check_all_heartbeats,
        trigger='interval',
        days=1,
        id='daily_heartbeat_check',
        replace_existing=True,
    )
    scheduler.add_job(
        check_scheduled_releases,
        trigger='interval',
        days=1,
        id='daily_scheduled_release_check',
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Killswitch scheduler started")
