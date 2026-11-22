from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import EmailOTP, NomineeRole, User, UserProfile


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
