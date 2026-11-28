from types import SimpleNamespace

from django.core import mail
from django.test import TestCase, override_settings

from .services import send_release_notification_email


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='afterlife@example.com',
    FRONTEND_URL='https://afterlife.example',
)
class LegacyAIReleaseNotificationTests(TestCase):
    def test_ai_only_release_includes_beneficiary_chat_route(self):
        nominee = SimpleNamespace(
            login_account=None,
            nominee_name='Trusted Person',
            nominee_email='beneficiary@example.com',
        )

        result = send_release_notification_email(
            nominee,
            0,
            legacy_ai_available=True,
        )

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/beneficiary/legacy-chat', mail.outbox[0].body)
        self.assertIn('third-party data-processing notice', mail.outbox[0].body)
