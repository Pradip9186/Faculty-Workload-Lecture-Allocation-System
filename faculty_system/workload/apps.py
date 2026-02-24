from django.apps import AppConfig


class WorkloadConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workload'

    def ready(self):
        # Clear all session records at startup so previously logged-in users
        # are forced to re-authenticate when the project runs.
        try:
            from django.contrib.sessions.models import Session
            Session.objects.all().delete()
        except Exception:
            # Avoid raising errors during migrations/startup
            pass
