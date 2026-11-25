from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
import re
import tempfile
import uuid
from types import SimpleNamespace
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import Credentials, EmailOTP, Nominee, NomineeRole, User, UserProfile, VaultItem
from .serializers import CredentialsSerializer, LegacyAIAccessSerializer, VaultItemSerializer


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RegistrationVerificationTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.registration_data = {
			'full_name': 'Test Person',
			'email': 'test@example.com',
			'password': 'StrongPass1!',
			'gender': 'Other',
		}

	def test_registration_creates_inactive_user_and_sends_code(self):
		response = self.client.post('/api/register/', self.registration_data, format='json')

		self.assertEqual(response.status_code, 201)
		user = User.objects.get(email=self.registration_data['email'])
		self.assertFalse(user.is_active)
		self.assertTrue(UserProfile.objects.filter(user=user).exists())
		self.assertEqual(EmailOTP.objects.filter(user=user, purpose='register').count(), 1)
		self.assertEqual(len(mail.outbox), 1)

	def test_verification_activates_user_and_returns_tokens(self):
		self.client.post('/api/register/', self.registration_data, format='json')
		user = User.objects.get(email=self.registration_data['email'])
		otp = EmailOTP.objects.get(user=user, purpose='register')

		response = self.client.post('/api/register/verify/', {
			'email': user.email,
			'otp': otp.otp_code,
		}, format='json')

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.data['access'])
		self.assertTrue(response.data['refresh'])
		user.refresh_from_db()
		otp.refresh_from_db()
		self.assertTrue(user.is_active)
		self.assertTrue(otp.is_used)

	def test_weak_password_is_rejected(self):
		data = {**self.registration_data, 'password': 'password'}

		response = self.client.post('/api/register/', data, format='json')

		self.assertEqual(response.status_code, 400)
		self.assertIn('password', response.data)

	def test_invalid_phone_is_rejected(self):
		data = {**self.registration_data, 'phone': '123'}

		response = self.client.post('/api/register/', data, format='json')

		self.assertEqual(response.status_code, 400)
		self.assertIn('phone', response.data)

	def test_duplicate_email_is_rejected(self):
		self.client.post('/api/register/', self.registration_data, format='json')

		response = self.client.post('/api/register/', self.registration_data, format='json')

		self.assertEqual(response.status_code, 400)
		self.assertIn('email', response.data)

	def test_nominee_can_be_invited_with_name_and_email_only(self):
		owner = User.objects.create_user(
			username='owner@example.com',
			email='owner@example.com',
			password='StrongPass1!',
			first_name='Vault Owner',
		)
		self.client.force_authenticate(user=owner)

		response = self.client.post('/nominees/', {
			'nominee_name': 'Trusted Person',
			'nominee_email': 'nominee@example.com',
		}, format='json')

		self.assertEqual(response.status_code, 201)
		self.assertTrue(response.data['invitation_sent'])
		self.assertEqual(response.data['nominee_phone'], '')
		self.assertEqual(response.data['relationship'], 'other')
		self.assertTrue(NomineeRole.objects.filter(nominee_id=response.data['id'], role='witness').exists())
		self.assertEqual(len(mail.outbox), 1)

	def test_onboarding_saves_timeout_for_authenticated_user(self):
		user = User.objects.create_user(
			username='owner@example.com',
			email='owner@example.com',
			password='StrongPass1!',
		)
		profile = UserProfile.objects.create(user=user)
		self.client.force_authenticate(user=user)

		response = self.client.patch('/api/onboarding/complete/', {
			'timeout_days': 30,
			'onboarding_completed': True,
		}, format='json')

		self.assertEqual(response.status_code, 200)
		profile.refresh_from_db()
		self.assertEqual(profile.timeout_days, 30)
		self.assertTrue(profile.onboarding_completed)

	def test_login_returns_jwt_tokens_for_active_user(self):
		user = User.objects.create_user(
			username='active@example.com',
			email='active@example.com',
			password='StrongPass1!',
			first_name='Active',
			last_name='User',
		)
		UserProfile.objects.create(user=user)

		response = self.client.post('/api/login/', {
			'email': 'active@example.com',
			'password': 'StrongPass1!',
		}, format='json')

		self.assertEqual(response.status_code, 200)
		self.assertIn('access', response.data)
		self.assertIn('refresh', response.data)
		self.assertFalse(response.data.get('onboarding_completed', True))


@override_settings(
	EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
	FIELD_ENCRYPTION_KEY='MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=',
)
class TrustedCircleTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.owner = User.objects.create_user(
			username='circle-owner@example.com',
			email='circle-owner@example.com',
			password='StrongPass1!',
		)
		UserProfile.objects.create(user=self.owner)
		self.client.force_authenticate(user=self.owner)

	def _invite(self, email, roles):
		return self.client.post('/nominees/', {
			'nominee_name': 'Trusted Person',
			'nominee_email': email,
			'roles': roles,
		}, format='json')

	def _invitation_token(self, email):
		message = next(item.body for item in mail.outbox if email in item.to)
		match = re.search(r'/nominee-invitation/([^\s]+)', message)
		self.assertIsNotNone(match)
		return match.group(1)

	def test_each_role_has_an_independent_explicit_invitation_decision(self):
		response = self._invite(
			'contact@example.com',
			['witness', 'beneficiary'],
		)
		self.assertEqual(response.status_code, 201)
		self.assertEqual(len(mail.outbox), 2)

		roles = {
			role.role: role
			for role in NomineeRole.objects.filter(nominee_id=response.data['id'])
		}
		beneficiary_token = self._invitation_token('contact@example.com')
		invitation_path = f'/api/nominee/confirm/{beneficiary_token}/'

		details = self.client.get(invitation_path)
		self.assertEqual(details.status_code, 200)
		self.assertEqual(details.data['role'], 'beneficiary')
		roles['beneficiary'].refresh_from_db()
		self.assertEqual(roles['beneficiary'].consent_status, 'pending')

		decision = self.client.post(
			invitation_path,
			{'decision': 'accept'},
			format='json',
		)
		self.assertEqual(decision.status_code, 200)
		roles['beneficiary'].refresh_from_db()
		roles['witness'].refresh_from_db()
		self.assertEqual(roles['beneficiary'].consent_status, 'accepted')
		self.assertEqual(roles['witness'].consent_status, 'pending')

		repeated_decision = self.client.post(
			invitation_path,
			{'decision': 'accept'},
			format='json',
		)
		self.assertEqual(repeated_decision.status_code, 200)

	def test_contact_email_cannot_change_without_a_reinvitation_flow(self):
		response = self._invite('contact@example.com', ['beneficiary'])
		self.assertEqual(response.status_code, 201)

		update = self.client.patch(
			f"/nominees/{response.data['id']}/",
			{'nominee_email': 'different@example.com'},
			format='json',
		)

		self.assertEqual(update.status_code, 400)
		self.assertIn('nominee_email', update.data)
		self.assertEqual(
			Nominee.objects.get(pk=response.data['id']).nominee_email,
			'contact@example.com',
		)

	def test_credentials_require_an_accepted_beneficiary_owned_by_the_user(self):
		response = self._invite('pending@example.com', ['beneficiary'])
		self.assertEqual(response.status_code, 201)
		nominee = Nominee.objects.get(pk=response.data['id'])
		payload = {
			'platform': 'Example',
			'platform_url': 'https://example.com',
			'username_on_platform': 'member',
			'email_on_platform': 'member@example.com',
			'password': 'secret-value',
			'assigned_nominee_id': nominee.id,
		}

		pending_serializer = CredentialsSerializer(
			data=payload,
			context={'request': SimpleNamespace(user=self.owner)},
		)
		self.assertFalse(pending_serializer.is_valid())
		self.assertIn('assigned_nominee_id', pending_serializer.errors)

		other_owner = User.objects.create_user(
			username='other-owner@example.com',
			email='other-owner@example.com',
			password='StrongPass1!',
		)
		other_nominee = Nominee.objects.create(
			user=other_owner,
			nominee_name='Other Person',
			nominee_email='other-contact@example.com',
			relationship='friend',
		)
		NomineeRole.objects.create(
			nominee=other_nominee,
			role='beneficiary',
			consent_status='accepted',
		)
		cross_owner_payload = {**payload, 'assigned_nominee_id': other_nominee.id}
		cross_owner_serializer = CredentialsSerializer(
			data=cross_owner_payload,
			context={'request': SimpleNamespace(user=self.owner)},
		)
		self.assertFalse(cross_owner_serializer.is_valid())
		self.assertIn('assigned_nominee_id', cross_owner_serializer.errors)

	def test_accepted_beneficiary_can_receive_a_credential_assignment_without_secret_in_response(self):
		response = self._invite('accepted@example.com', ['beneficiary'])
		token = self._invitation_token('accepted@example.com')
		decision = self.client.post(
			f'/api/nominee/confirm/{token}/',
			{'decision': 'accept'},
			format='json',
		)
		self.assertEqual(decision.status_code, 200)

		response = self.client.post('/api/credentials/', {
			'platform': 'Example',
			'platform_url': 'https://example.com',
			'username_on_platform': 'member',
			'email_on_platform': 'member@example.com',
			'password': 'secret-value',
			'assigned_nominee_id': response.data['id'],
		}, format='json')
		self.assertEqual(response.status_code, 201)
		self.assertNotIn('password', response.data)

	def test_memory_capsules_require_an_accepted_beneficiary_owned_by_the_user(self):
		response = self._invite('capsule-contact@example.com', ['beneficiary'])
		nominee = Nominee.objects.get(pk=response.data['id'])
		payload = {
			'title': 'Family letter',
			'file': SimpleUploadedFile('letter.pdf', b'example', content_type='application/pdf'),
			'recipient': nominee.id,
			'release_type': 'killswitch',
		}
		serializer = VaultItemSerializer(
			data=payload,
			context={'request': SimpleNamespace(user=self.owner)},
		)
		self.assertFalse(serializer.is_valid())
		self.assertIn('recipient', serializer.errors)

		nominee.roles.filter(role='beneficiary').update(consent_status='accepted')
		payload['file'] = SimpleUploadedFile('letter.pdf', b'example', content_type='application/pdf')
		serializer = VaultItemSerializer(
			data=payload,
			context={'request': SimpleNamespace(user=self.owner)},
		)
		self.assertTrue(serializer.is_valid(), serializer.errors)

	def test_legacy_ai_assignment_requires_an_accepted_beneficiary(self):
		response = self._invite('ai-contact@example.com', ['beneficiary'])
		nominee = Nominee.objects.get(pk=response.data['id'])
		context = {'request': SimpleNamespace(user=self.owner)}

		serializer = LegacyAIAccessSerializer(
			data={'nominee': nominee.id},
			context=context,
		)
		self.assertFalse(serializer.is_valid())
		self.assertIn('nominee', serializer.errors)

		nominee.roles.filter(role='beneficiary').update(consent_status='accepted')
		serializer = LegacyAIAccessSerializer(
			data={'nominee': nominee.id},
			context=context,
		)
		self.assertTrue(serializer.is_valid(), serializer.errors)

	def test_failed_invitation_delivery_is_reported_and_can_be_retried(self):
		with patch('FYP_app.emails.send_mail', side_effect=OSError('smtp unavailable')):
			response = self._invite('retry@example.com', ['beneficiary'])
		self.assertEqual(response.status_code, 201)
		self.assertFalse(response.data['invitation_sent'])

		role = NomineeRole.objects.get(nominee_id=response.data['id'])
		self.assertIsNone(role.invitation_sent_at)
		with patch('FYP_app.emails.send_mail', return_value=1):
			retry = self.client.post(
				f"/nominees/{response.data['id']}/resend-invitation/",
				{},
				format='json',
			)
		self.assertEqual(retry.status_code, 200)
		self.assertTrue(retry.data['invitation_sent'])
		role.refresh_from_db()
		self.assertIsNotNone(role.invitation_sent_at)

	def test_trusted_circle_settings_require_two_witnesses_and_freeze_during_warning(self):
		response = self.client.patch(
			'/api/trusted-circle/settings/',
			{'witness_quorum': 1},
			format='json',
		)
		self.assertEqual(response.status_code, 400)

		response = self.client.patch(
			'/api/trusted-circle/settings/',
			{'witness_quorum': 3},
			format='json',
		)
		self.assertEqual(response.status_code, 200)
		self.assertFalse(response.data['ready'])
		self.assertEqual(response.data['accepted_witnesses'], 0)

		profile = self.owner.profile
		profile.status = 'warning'
		profile.release_quorum_snapshot = 3
		profile.save(update_fields=['status', 'release_quorum_snapshot'])
		response = self.client.patch(
			'/api/trusted-circle/settings/',
			{'witness_quorum': 2},
			format='json',
		)
		self.assertEqual(response.status_code, 400)


@override_settings(
	FIELD_ENCRYPTION_KEY='MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=',
)
class WitnessQuorumTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username='quorum-owner@example.com',
			email='quorum-owner@example.com',
			password='StrongPass1!',
		)
		self.profile = UserProfile.objects.create(
			user=self.user,
			status='warning',
			witness_quorum=2,
			release_quorum_snapshot=2,
		)

	def _witness_role(self, suffix):
		nominee = Nominee.objects.create(
			user=self.user,
			nominee_name=f'Witness {suffix}',
			nominee_email=f'witness{suffix}@example.com',
			relationship='friend',
		)
		return NomineeRole.objects.create(
			nominee=nominee,
			role='witness',
			consent_status='accepted',
			vote_token=uuid.uuid4(),
		)

	def test_two_distinct_witnesses_are_required_and_a_vote_cannot_be_counted_twice(self):
		first = self._witness_role('one')
		self._witness_role('two')
		self._witness_role('three')

		from killswitch.legacy_release import record_witness_vote

		first_vote, status_code = record_witness_vote(first.vote_token, 'death')
		self.assertEqual(status_code, 200)
		self.assertEqual(first_vote['status'], 'warning')
		self.profile.refresh_from_db()
		self.assertEqual(self.profile.status, 'warning')

		replayed_vote, status_code = record_witness_vote(first.vote_token, 'death')
		self.assertEqual(status_code, 200)
		self.assertEqual(replayed_vote['message'], 'Your vote has already been recorded.')
		self.assertEqual(
			NomineeRole.objects.filter(
				nominee__user=self.user,
				vote='death',
			).count(),
			1,
		)

		second = NomineeRole.objects.exclude(pk=first.pk).first()
		final_vote, status_code = record_witness_vote(second.vote_token, 'death')
		self.assertEqual(status_code, 200)
		self.assertEqual(final_vote['status'], 'released')
		self.profile.refresh_from_db()
		self.assertEqual(self.profile.status, 'released')

	def test_unaccepted_or_insufficient_witnesses_cannot_release_assets(self):
		accepted = self._witness_role('accepted')
		pending = self._witness_role('pending')
		pending.consent_status = 'pending'
		pending.save(update_fields=['consent_status'])
		from killswitch.legacy_release import record_witness_vote

		data, status_code = record_witness_vote(accepted.vote_token, 'death')
		self.assertEqual(status_code, 200)
		self.assertEqual(data['status'], 'warning')
		self.assertEqual(data['eligible_witnesses'], 1)

		data, status_code = record_witness_vote(pending.vote_token, 'death')
		self.assertEqual(status_code, 404)
		self.assertEqual(data['error'], 'This witness link is invalid or expired.')
		self.profile.refresh_from_db()
		self.assertEqual(self.profile.status, 'warning')

	def test_death_quorum_releases_only_assets_assigned_to_accepted_beneficiaries(self):
		accepted_nominee = Nominee.objects.create(
			user=self.user,
			nominee_name='Accepted Beneficiary',
			nominee_email='accepted-beneficiary@example.com',
			relationship='friend',
		)
		NomineeRole.objects.create(
			nominee=accepted_nominee,
			role='beneficiary',
			consent_status='accepted',
		)
		pending_nominee = Nominee.objects.create(
			user=self.user,
			nominee_name='Pending Beneficiary',
			nominee_email='pending-beneficiary@example.com',
			relationship='friend',
		)
		NomineeRole.objects.create(
			nominee=pending_nominee,
			role='beneficiary',
			consent_status='pending',
		)
		accepted_credential = Credentials.objects.create(
			user=self.user,
			platform='Accepted platform',
			platform_url='https://accepted.example.com',
			username_on_platform='accepted',
			email_on_platform='accepted@example.com',
			password='secret',
			assigned_nominee=accepted_nominee,
		)
		pending_credential = Credentials.objects.create(
			user=self.user,
			platform='Pending platform',
			platform_url='https://pending.example.com',
			username_on_platform='pending',
			email_on_platform='pending@example.com',
			password='secret',
			assigned_nominee=pending_nominee,
		)
		first = self._witness_role('death-one')
		second = self._witness_role('death-two')

		from killswitch.legacy_release import record_witness_vote

		record_witness_vote(first.vote_token, 'death')
		result, status_code = record_witness_vote(second.vote_token, 'death')
		self.assertEqual(status_code, 200)
		self.assertEqual(result['status'], 'released')
		accepted_credential.refresh_from_db()
		pending_credential.refresh_from_db()
		self.assertEqual(accepted_credential.status, 'released')
		self.assertEqual(pending_credential.status, 'locked')


class ReleasedCapsuleAccessTests(TestCase):
	def setUp(self):
		self.media_dir = tempfile.TemporaryDirectory()
		override = override_settings(MEDIA_ROOT=self.media_dir.name)
		override.enable()
		self.addCleanup(override.disable)
		self.addCleanup(self.media_dir.cleanup)

		self.owner = User.objects.create_user(
			username='capsule-owner@example.com',
			email='capsule-owner@example.com',
			password='StrongPass1!',
		)
		UserProfile.objects.create(user=self.owner, status='released')
		self.beneficiary = User.objects.create_user(
			username='capsule-beneficiary@example.com',
			email='capsule-beneficiary@example.com',
			password='StrongPass1!',
		)
		self.nominee = Nominee.objects.create(
			user=self.owner,
			nominee_name='Capsule Beneficiary',
			nominee_email=self.beneficiary.email,
			relationship='friend',
			login_account=self.beneficiary,
		)
		NomineeRole.objects.create(
			nominee=self.nominee,
			role='beneficiary',
			consent_status='accepted',
		)
		self.item = VaultItem.objects.create(
			user=self.owner,
			title='Private letter',
			file=SimpleUploadedFile('letter.pdf', b'private contents', content_type='application/pdf'),
			recipient=self.nominee,
			is_sent=True,
		)
		self.client = APIClient()

	def test_download_requires_an_accepted_assignee_and_released_capsule(self):
		self.client.force_authenticate(user=self.beneficiary)
		response = self.client.get(f'/my-assets/capsules/{self.item.id}/file/')
		self.assertEqual(response.status_code, 200)
		self.assertIn('attachment', response['Content-Disposition'])
		self.assertEqual(b''.join(response.streaming_content), b'private contents')

		self.item.is_sent = False
		self.item.save(update_fields=['is_sent'])
		response = self.client.get(f'/my-assets/capsules/{self.item.id}/file/')
		self.assertEqual(response.status_code, 404)

	def test_vault_file_url_is_not_exposed_or_served_as_public_media(self):
		self.client.force_authenticate(user=self.owner)
		response = self.client.get('/vault-items/')
		self.assertEqual(response.status_code, 200)
		self.assertNotIn('file', response.data[0])

		response = self.client.get('/media/vault_files/letter.pdf')
		self.assertEqual(response.status_code, 404)

	def test_owner_can_download_their_private_capsule_only_before_release(self):
		profile = self.owner.profile
		profile.status = 'active'
		profile.save(update_fields=['status'])
		self.item.is_sent = False
		self.item.save(update_fields=['is_sent'])

		self.client.force_authenticate(user=self.owner)
		response = self.client.get(f'/my-assets/capsules/{self.item.id}/file/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(b''.join(response.streaming_content), b'private contents')
