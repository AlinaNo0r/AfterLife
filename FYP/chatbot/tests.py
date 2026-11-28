import json
import tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from FYP_app.models import LegacyAIAccess, Nominee, NomineeRole, User, UserProfile

from .models import BeneficiaryPersona, LegacyConversation, LegacyMessage, MemorySource


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class LegacyAIAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner@example.com',
            email='owner@example.com',
            password='StrongPass1!',
            first_name='Owner',
        )
        self.profile = UserProfile.objects.create(user=self.owner, status='active')
        self.beneficiary_user = User.objects.create_user(
            username='beneficiary@example.com',
            email='beneficiary@example.com',
            password='StrongPass1!',
            first_name='Beneficiary',
        )
        self.nominee = Nominee.objects.create(
            user=self.owner,
            nominee_name='Trusted Person',
            nominee_email='beneficiary@example.com',
            nominee_phone='',
            relationship='child',
            login_account=self.beneficiary_user,
        )
        NomineeRole.objects.create(
            nominee=self.nominee,
            role='beneficiary',
            consent_status='accepted',
        )
        LegacyAIAccess.objects.create(user=self.owner, nominee=self.nominee)
        self.persona = BeneficiaryPersona.objects.create(
            owner=self.owner,
            nominee=self.nominee,
            owner_data_consent_at=timezone.now(),
        )
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(self.owner)
        self.beneficiary_client = APIClient()
        self.beneficiary_client.force_authenticate(self.beneficiary_user)

    def test_owner_can_upload_scoped_text_and_get_readiness_warning(self):
        with patch('chatbot.views.embed_texts', return_value=[[1.0, 0.0]]):
            response = self.owner_client.post(
                '/api/legacy-ai/owner/sources/',
                {
                    'nominee_ids': json.dumps([self.nominee.id]),
                    'text': 'A small memory about family and kindness.',
                    'display_name': 'A short memory',
                },
                format='multipart',
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(MemorySource.objects.get().beneficiaries.get(), self.nominee)
        readiness = response.data['beneficiaries'][0]['readiness']
        self.assertTrue(readiness['not_model_training'])
        self.assertFalse(readiness['ready_for_personalized_responses'])
        self.assertGreater(readiness['words_needed'], 0)

    def test_upload_rejects_unassigned_beneficiary(self):
        other = Nominee.objects.create(
            user=self.owner,
            nominee_name='Other Person',
            nominee_email='other@example.com',
            nominee_phone='',
            relationship='friend',
        )
        NomineeRole.objects.create(
            nominee=other,
            role='beneficiary',
            consent_status='accepted',
        )
        response = self.owner_client.post(
            '/api/legacy-ai/owner/sources/',
            {
                'nominee_ids': json.dumps([other.id]),
                'text': 'A private memory',
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(MemorySource.objects.exists())

    def test_uploaded_memory_is_not_included_in_another_beneficiary_readiness(self):
        other = Nominee.objects.create(
            user=self.owner,
            nominee_name='Another Person',
            nominee_email='another@example.com',
            nominee_phone='',
            relationship='friend',
        )
        NomineeRole.objects.create(
            nominee=other,
            role='beneficiary',
            consent_status='accepted',
        )
        LegacyAIAccess.objects.create(user=self.owner, nominee=other)
        BeneficiaryPersona.objects.create(
            owner=self.owner,
            nominee=other,
            owner_data_consent_at=timezone.now(),
        )
        with patch('chatbot.views.embed_texts', return_value=[[1.0, 0.0]]):
            self.owner_client.post(
                '/api/legacy-ai/owner/sources/',
                {
                    'nominee_ids': json.dumps([self.nominee.id]),
                    'text': 'A memory about kindness and family.',
                },
                format='multipart',
            )

        self.assertGreater(
            self.client_readiness(self.nominee)['word_count'],
            0,
        )
        self.assertEqual(self.client_readiness(other)['word_count'], 0)

    def test_owner_can_preview_a_reply_without_creating_beneficiary_chat_history(self):
        with (
            patch('chatbot.views.retrieve_memories', return_value=[]),
            patch(
                'chatbot.views.generate_legacy_reply',
                return_value='This is a private preview reply.',
            ) as generate_reply,
        ):
            response = self.owner_client.post(
                f'/api/legacy-ai/owner/preview/{self.nominee.id}/',
                {
                    'message': 'What was important to you?',
                    'history': [{'role': 'user', 'content': 'Hello'}],
                },
                format='json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message']['content'], 'This is a private preview reply.')
        self.assertFalse(response.data['saved'])
        self.assertFalse(LegacyConversation.objects.exists())
        self.assertFalse(LegacyMessage.objects.exists())
        self.assertEqual(
            generate_reply.call_args.kwargs['conversation_history'],
            [{'role': 'user', 'content': 'Hello'}],
        )

    def test_owner_preview_requires_saved_provider_consent(self):
        self.persona.owner_data_consent_at = None
        self.persona.save(update_fields=['owner_data_consent_at'])

        response = self.owner_client.post(
            f'/api/legacy-ai/owner/preview/{self.nominee.id}/',
            {'message': 'Can you share a memory?'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(LegacyConversation.objects.exists())

    @staticmethod
    def client_readiness(nominee):
        from .services import get_readiness

        return get_readiness(nominee)

    def test_beneficiary_must_accept_provider_notice_before_chat(self):
        self.profile.status = 'released'
        self.profile.save(update_fields=['status'])
        response = self.beneficiary_client.post(
            '/api/legacy-ai/beneficiary/chat/',
            {'message': 'Tell me about a memory'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(LegacyConversation.objects.exists())

    def test_withdrawing_beneficiary_consent_deletes_local_chat_history(self):
        self.profile.status = 'released'
        self.profile.save(update_fields=['status'])
        self.persona.beneficiary_processing_consent_at = timezone.now()
        self.persona.save(update_fields=['beneficiary_processing_consent_at'])
        conversation = LegacyConversation.objects.create(
            owner=self.owner,
            nominee=self.nominee,
        )
        LegacyMessage.objects.create(
            conversation=conversation,
            role='user',
            content='Please stop processing my messages.',
        )

        response = self.beneficiary_client.post(
            '/api/legacy-ai/beneficiary/consent/',
            {'accepted': False},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(LegacyConversation.objects.exists())
        self.persona.refresh_from_db()
        self.assertIsNone(self.persona.beneficiary_processing_consent_at)

    def test_released_beneficiary_can_chat_after_consent_and_messages_are_scoped(self):
        self.profile.status = 'released'
        self.profile.save(update_fields=['status'])
        self.beneficiary_client.post(
            '/api/legacy-ai/beneficiary/consent/',
            {'accepted': True},
            format='json',
        )
        with (
            patch('chatbot.views.retrieve_memories', return_value=[]),
            patch('chatbot.views.generate_legacy_reply', return_value='I do not have a specific memory to share.'),
        ):
            response = self.beneficiary_client.post(
                '/api/legacy-ai/beneficiary/chat/',
                {'message': 'Tell me about a memory'},
                format='json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message']['role'], 'assistant')
        conversation = LegacyConversation.objects.get(nominee=self.nominee)
        self.assertEqual(conversation.messages.count(), 2)
        self.assertEqual(LegacyMessage.objects.filter(conversation=conversation, role='user').count(), 1)

    def test_crisis_message_receives_local_safety_response_without_provider_call(self):
        self.profile.status = 'released'
        self.profile.save(update_fields=['status'])
        self.beneficiary_client.post(
            '/api/legacy-ai/beneficiary/consent/',
            {'accepted': True},
            format='json',
        )
        with patch('chatbot.views.generate_legacy_reply') as generate_reply:
            response = self.beneficiary_client.post(
                '/api/legacy-ai/beneficiary/chat/',
                {'message': 'I might hurt myself'},
                format='json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn('local emergency services', response.data['message']['content'])
        generate_reply.assert_not_called()

    @override_settings(LEGACY_OLLAMA_MODEL='')
    def test_missing_local_model_configuration_is_returned_as_an_explicit_error(self):
        self.profile.status = 'released'
        self.profile.save(update_fields=['status'])
        self.beneficiary_client.post(
            '/api/legacy-ai/beneficiary/consent/',
            {'accepted': True},
            format='json',
        )
        with patch('chatbot.views.retrieve_memories', return_value=[]):
            response = self.beneficiary_client.post(
                '/api/legacy-ai/beneficiary/chat/',
                {'message': 'Can you share a memory?'},
                format='json',
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn('LEGACY_OLLAMA_MODEL', response.data['error'])
        self.assertFalse(LegacyConversation.objects.exists())

    def test_reply_generation_uses_the_configured_local_ollama_chat_endpoint(self):
        from .services import generate_legacy_reply

        with (
            patch('chatbot.services.urllib.request.urlopen') as fake_response,
            override_settings(
                LEGACY_OLLAMA_MODEL='qwen2.5:3b',
                LEGACY_OLLAMA_URL='http://127.0.0.1:11434',
            ),
        ):
            fake_response.return_value.__enter__.return_value.read.return_value = json.dumps({
                'message': {'content': 'A local reply.'},
            }).encode('utf-8')
            answer = generate_legacy_reply(
                self.persona,
                'Tell me something about our family.',
                [],
                {'ready_for_personalized_responses': False},
            )

        self.assertEqual(answer, 'A local reply.')
        request = fake_response.call_args.args[0]
        self.assertEqual(request.full_url, 'http://127.0.0.1:11434/api/chat')
        body = json.loads(request.data.decode('utf-8'))
        self.assertEqual(body['model'], 'qwen2.5:3b')
        self.assertFalse(body['stream'])
        self.assertEqual(body['messages'][-1]['content'], 'Tell me something about our family.')

    def test_chat_is_blocked_until_owner_release(self):
        self.profile.status = 'active'
        self.profile.save(update_fields=['status'])
        response = self.beneficiary_client.get('/api/legacy-ai/beneficiary/')

        self.assertEqual(response.status_code, 403)
