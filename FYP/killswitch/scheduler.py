from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import UserProfile 
from .services import notify_nominees_warning, release_assets, check_scheduled_releases
import os

User = get_user_model()

scheduler_started = False

def check_inactive_users():
    print("Running Kill Switch check...")
    now = timezone.now()

    # Stage 1: active -> warning
    active_profiles = UserProfile.objects.filter(status='active')
    for profile in active_profiles:
        days_silent = (now - profile.last_seen).days
        if days_silent >= profile.timeout_days:
            profile.status = 'warning'
            profile.warning_start = now
            profile.save()
            print(f"User {profile.user.username} moved to WARNING status.")

    # Stage 2: warning -> fallback (agar 50 din tak koi majority na bane)
    warning_profiles = UserProfile.objects.filter(status='warning')
    for profile in warning_profiles:
        days_in_warning = (now - profile.warning_start).days
        if days_in_warning >= 120:
            profile.status = 'fallback'
            profile.save()
            print(f"User {profile.user.username} moved to FALLBACK — no majority reached.")

def start_scheduler():
    global scheduler_started
    if scheduler_started:
        return

    if os.environ.get('RUN_MAIN') != 'true':
        return

    scheduler = BackgroundScheduler()
    # scheduler.add_job(check_inactive_users, 'interval', days=1)
    # scheduler.add_job(check_scheduled_releases, 'interval', days=1)  
    scheduler.add_job(check_scheduled_releases, 'interval', minutes=1)  

    
    
    scheduler.add_job(check_inactive_users, 'interval', minutes=1)

    scheduler.start()
    scheduler_started = True
    print("Kill Switch Scheduler started.")