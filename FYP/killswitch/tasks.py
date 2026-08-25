# killswitch/tasks.py

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def check_all_heartbeats():
    """
    Daily Killswitch Checker - Full Escalation Logic
    Follows this flow:
    1. Active → Warning (email witnesses)
    2. Warning period over → Triggered (start release process)
    """
    from FYP_app.models import UserProfile   
    logger.info(" Daily Check Started...")

    now = timezone.now()
    
   
    profiles = UserProfile.objects.filter(status__in=['active', 'warning'])

    for profile in profiles:
        try:
            with transaction.atomic():
                # Lock database row from external changes until this loop completes
                profile = UserProfile.objects.select_for_update().get(pk=profile.pk)
                # Use standard fallback default if field is missing or null
                timeout_limit = getattr(profile, 'timeout_days', 30) or 30
                days_since_last_seen = (now - profile.last_seen).days

            # days_since_last_seen = (now - profile.last_seen).days

            if days_since_last_seen <= profile.timeout_days:
                continue

             # === STEP 1: Active → Warning ===
            if profile.status == 'active':
                profile.status = 'warning'
                profile.warning_start = now
                profile.save(update_fields=['status', 'warning_start'])
                
                profile.notify_nominees_warning()   # Witnesses ko email
                
                logger.warning(f"⚠️ WARNING triggered for {profile.user.username} "
                             f"({days_since_last_seen} days missed)")

        #     # === STEP 2: Warning → inactive ===
        #     elif profile.status == 'warning':
        #         days_in_warning = (now - profile.warning_start).days
                
        #         if days_in_warning > 7:         
        #             profile.status = 'inactive'
        #             profile.save(update_fields=['status'])
                    
        #             logger.critical(f"🚨 Inactivity detected for {profile.user.username} - Starting release Process")
        #             profile.start_release_process()   # Assets release process shuru

        # except Exception as e:
        #     logger.error(f"Error checking killswitch for user "
        #                 f"{getattr(profile.user, 'username', 'Unknown')}: {e}")


        # -------------------------------------------------------------------
                    # === STEP 2: Warning Phase Milestone Evaluation ===
            elif profile.status == 'warning':
                if profile.warning_start:
                    days_in_warning = (now - profile.warning_start).days
                else:
                    days_in_warning = 0
                
                # If the user has failed to check in during the 7-day grace period
                if days_in_warning > 7:         
                    logger.warning(f"⏳ Grace period over for {profile.user.username}. Dispatched confirmation request to nominees.")
                    
                    # 🔒 SECURITY UPDATE: Instead of a blind data dump, dispatch the interactive decision webhooks to nominees
                    from FYP_app.emails import send_nominee_verification_email
                    
                    # Fetch all saved nominees for this specific user profile
                    witnesses = profile.user.nominees.all()
                    
                    if not witnesses.exists():
                        logger.error(f"❌ Missing Nominees: Cannot escalate validation for user {profile.user.username}")
                        continue
                        
                    # Loop through nominees and fire the customized verification template emails
                    for nominee in witnesses:
                        send_nominee_verification_email(
                            nominee_email=nominee.nominee_email,
                            nominee_name=nominee.nominee_name,
                            owner_name=profile.user.get_full_name() or profile.user.username,
                            profile_id=profile.id  # Passes database context primary row ID for the email link
                        )
                        
                    # Note: We keep their status as 'warning' for now. 
                    # The status changes to 'inactive' ONLY if a nominee clicks the "Deceased Link" view button.

        except Exception as e:
            logger.error(f"Error checking killswitch for user {getattr(profile.user, 'username', 'Unknown')}: {e}")
#------------------------------------------------------------------------------------------------------------------------------------------------

    logger.info("✅ Daily Check Completed.")


def start_scheduler():
    if scheduler.running:
        logger.info("Scheduler already running, skipping...")
        return

    try:
        scheduler.add_job(
            check_all_heartbeats,
            trigger=IntervalTrigger(days=1),          
            id='daily_check',
            replace_existing=True,                    #replacing existing job if it exists
            next_run_time=timezone.now() + timezone.timedelta(seconds=30)  # Testing ke liye jaldi
        )
        
        scheduler.start()
        logger.info(" Killswitch Scheduler Started Successfully!")
        
    except Exception as e:
        logger.error(f"Failed to start Killswitch scheduler: {e}")