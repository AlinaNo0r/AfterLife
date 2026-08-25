from django.apps import AppConfig
import os

class KillswitchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'killswitch'

    def ready(self):
        """
        🔒 SECURITY UPDATE: Automatically initializes the background killswitch
        scheduler thread as soon as the Django server boots up.
        """
        # Safe Guard Check: Prevents Django's auto-reloader from spinning up 
        # a duplicate scheduler thread inside your local computer memory (RAM).
        if os.environ.get('RUN_MAIN') == 'true':
            from .tasks import start_scheduler
            start_scheduler()
