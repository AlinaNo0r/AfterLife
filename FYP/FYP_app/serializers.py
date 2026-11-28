import re
import uuid

from rest_framework import serializers
from django.contrib.auth import password_validation
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import (
    Credentials,
    LegacyAIAccess,
    Nominee,
    NomineeRole,
    VaultItem,
    UserProfile,
)

User = get_user_model()


class NomineeSerializer(serializers.ModelSerializer):
    roles = serializers.MultipleChoiceField(
        choices=[('witness', 'Death Witness'), ('beneficiary', 'Beneficiary')],
        write_only=True,
        required=False,
        default=['witness'],
    )
    role_statuses = serializers.SerializerMethodField()

    class Meta:
        model = Nominee
        fields = [
            'id',
            'nominee_name',
            'nominee_email',
            'nominee_phone',
            'relationship',
            'user',
            'roles',
            'role_statuses',
        ]
        read_only_fields = ['user']
        extra_kwargs = {
            'nominee_phone': {'required': False, 'allow_blank': True},
            'relationship': {'required': False},
        }

    def get_role_statuses(self, nominee):
        return [
            {
                'id': role.id,
                'role': role.role,
                'consent_status': role.consent_status,
                'invitation_sent_at': role.invitation_sent_at,
                'confirmed_at': role.confirmed_at,
            }
            for role in nominee.roles.order_by('role')
        ]

    def validate(self, attrs):
        roles = attrs.get('roles')
        instance = self.instance
        if roles is not None and not roles:
            raise serializers.ValidationError(
                {'roles': 'Select at least one role for this contact.'}
            )
        if (
            instance is not None
            and 'nominee_email' in attrs
            and attrs['nominee_email'].casefold() != instance.nominee_email.casefold()
        ):
            raise serializers.ValidationError({
                'nominee_email': (
                    'A contact email cannot be changed after creation. Remove and re-add '
                    'the contact; reassign any assets first.'
                )
            })

        request = self.context.get('request')
        nominee_email = attrs.get(
            'nominee_email',
            instance.nominee_email if instance is not None else None,
        )
        if instance is None and request is not None and nominee_email:
            duplicate_contact = Nominee.objects.filter(
                user=request.user,
                nominee_email__iexact=nominee_email,
            ).exists()
            if duplicate_contact:
                raise serializers.ValidationError({
                    'nominee_email': 'This email is already in your Trusted Circle. Edit the existing contact instead.'
                })

        if roles is not None:
            roles_to_apply = set(roles)
        elif instance is not None:
            roles_to_apply = set(instance.roles.values_list('role', flat=True))
        else:
            roles_to_apply = set()
        if 'beneficiary' in roles_to_apply and nominee_email:
            login_user = User.objects.filter(email__iexact=nominee_email).first()
            if login_user is not None:
                linked_contacts = Nominee.objects.filter(login_account=login_user)
                if instance is not None:
                    linked_contacts = linked_contacts.exclude(pk=instance.pk)
                if linked_contacts.exists():
                    raise serializers.ValidationError({
                        'nominee_email': (
                            'This email is already linked to another beneficiary account. '
                            'Use that existing contact instead.'
                        )
                    })

        if roles is None or instance is None:
            return attrs

        profile = UserProfile.objects.filter(user=instance.user).first()
        if profile and profile.status != 'active':
            raise serializers.ValidationError(
                {'roles': 'Roles cannot be changed while release verification is active.'}
            )

        removed_roles = set(instance.roles.values_list('role', flat=True)) - set(roles)
        if 'beneficiary' in removed_roles:
            if (
                instance.credentials.exists()
                or instance.vault_items.exists()
                or instance.legacy_ai_access.exists()
            ):
                raise serializers.ValidationError({
                    'roles': (
                        'Reassign this contact’s credentials, capsules, and Legacy AI access '
                        'before removing the beneficiary role.'
                    )
                })
        return attrs

    def create(self, validated_data):
        roles_data = validated_data.pop('roles', ['witness'])
        validated_data.setdefault('nominee_phone', '')
        validated_data.setdefault('relationship', 'other')
        validated_data['user'] = self.context['request'].user
        with transaction.atomic():
            nominee = Nominee.objects.create(**validated_data)
            for role in roles_data:
                NomineeRole.objects.create(nominee=nominee, role=role)
            if 'beneficiary' in roles_data:
                self._link_login_account(nominee)
        return nominee

    def update(self, instance, validated_data):
        roles_data = validated_data.pop('roles', None)
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if roles_data is not None:
                existing_roles = {
                    role.role: role for role in instance.roles.all()
                }
                for role_name in roles_data:
                    if role_name in existing_roles:
                        role = existing_roles[role_name]
                        if role.consent_status == 'declined':
                            role.consent_status = 'pending'
                            role.confirmed_at = None
                            role.invitation_sent_at = None
                            role.invitation_token = uuid.uuid4()
                            role.save(update_fields=[
                                'consent_status',
                                'confirmed_at',
                                'invitation_sent_at',
                                'invitation_token',
                            ])
                        continue
                    NomineeRole.objects.create(nominee=instance, role=role_name)
                for role_name, role in existing_roles.items():
                    if role_name not in roles_data:
                        role.delete()
                if 'beneficiary' in roles_data:
                    self._link_login_account(instance)
        return instance

    @staticmethod
    def _link_login_account(nominee):
        if nominee.login_account_id:
            return
        login_user = User.objects.filter(email__iexact=nominee.nominee_email).first()
        if login_user is None:
            login_user = User.objects.create_user(
                username=nominee.nominee_email,
                email=nominee.nominee_email,
                first_name=nominee.nominee_name,
            )
            login_user.set_unusable_password()
            login_user.save()
        nominee.login_account = login_user
        nominee.save(update_fields=['login_account'])




class NomineeRoleSerializer(serializers.ModelSerializer):
    nominee_name = serializers.CharField(source='nominee.nominee_name', read_only=True)

    class Meta:
        model = NomineeRole
        fields = [
            'id',
            'role',
            'nominee_name',
            'nominee',
            'consent_status',
            'confirmed_at',
            'vote',
            'voted_at',
        ]


class LegacyAIAccessSerializer(serializers.ModelSerializer):
    nominee_name = serializers.CharField(source='nominee.nominee_name', read_only=True)
    nominee_email = serializers.EmailField(source='nominee.nominee_email', read_only=True)

    class Meta:
        model = LegacyAIAccess
        fields = ['id', 'nominee', 'nominee_name', 'nominee_email', 'assigned_at']
        read_only_fields = ['assigned_at']

    def validate_nominee(self, nominee):
        if nominee.user_id != self.context['request'].user.id:
            raise serializers.ValidationError('Choose a contact from your Trusted Circle.')
        role = nominee.roles.filter(
            role='beneficiary',
            consent_status='accepted',
        ).first()
        if role is None:
            raise serializers.ValidationError(
                'Only contacts who accepted the beneficiary role can be assigned.'
            )
        return nominee


class CredentialsSerializer(serializers.ModelSerializer):
    nominee_details = NomineeSerializer(source='assigned_nominee', read_only=True)
    assigned_nominee_id = serializers.PrimaryKeyRelatedField(
        queryset=Nominee.objects.all(),
        source='assigned_nominee',
        write_only=True
    )

    class Meta:
        model = Credentials
        fields = [
            'id',
            'platform',
            'platform_url',
            'password',
            'username_on_platform',
            'email_on_platform',
            'password',
            'nominee_details',
            'assigned_nominee_id'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, attrs):
        nominee = attrs.get('assigned_nominee')
        if nominee is None and self.instance:
            nominee = self.instance.assigned_nominee
        if nominee is None:
            raise serializers.ValidationError(
                {'assigned_nominee_id': 'Choose a beneficiary for this credential.'}
            )
        if nominee.user_id != self.context['request'].user.id:
            raise serializers.ValidationError(
                {'assigned_nominee_id': 'Choose a contact from your Trusted Circle.'}
            )
        if not nominee.roles.filter(
            role='beneficiary',
            consent_status='accepted',
        ).exists():
            raise serializers.ValidationError(
                {'assigned_nominee_id': 'The contact must accept the beneficiary role first.'}
            )
        return attrs

class UserSerializer(serializers.ModelSerializer):
    onboarding_completed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'dob', 'gender', 'phone', 'onboarding_completed']

    def get_onboarding_completed(self, user):
        profile = getattr(user, 'profile', None)
        return profile.onboarding_completed if profile else False


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=['Male', 'Female', 'Other'])
    dob = serializers.DateField(required=False, allow_null=True)

    def validate_password(self, value):
        requirements = (
            (r'[A-Z]', 'one uppercase letter'),
            (r'\d', 'one number'),
            (r'[^A-Za-z0-9]', 'one special character'),
        )
        missing = [description for pattern, description in requirements if not re.search(pattern, value)]
        if missing:
            raise serializers.ValidationError(
                'Password must include ' + ', '.join(missing) + '.'
            )
        password_validation.validate_password(value)
        return value

    def validate_phone(self, value):
        cleaned_value = re.sub(r'[\s()-]', '', value or '')
        if value and not re.fullmatch(r'\+?[1-9]\d{6,14}', cleaned_value):
            raise serializers.ValidationError('Enter a valid phone number with country code, for example +923001234567.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        full_name = validated_data.pop('full_name')
        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=first_name,
            last_name=last_name,
            phone=validated_data.get('phone', ''),
            gender=validated_data.get('gender'),
            dob=validated_data.get('dob'),
            is_active=False,
        )
        return user


class OnboardingSerializer(serializers.Serializer):
    timeout_days = serializers.IntegerField(min_value=1, max_value=365, required=False)
    onboarding_completed = serializers.BooleanField(default=True)


class TrustedCircleSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['witness_quorum']
        extra_kwargs = {
            'witness_quorum': {
                'min_value': 2,
                'max_value': 20,
            }
        }

    def validate_witness_quorum(self, value):
        if self.instance and self.instance.status != 'active':
            raise serializers.ValidationError(
                'The witness quorum is frozen while release verification is active.'
            )
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context['user']
        if not user.check_password(value):
            raise serializers.ValidationError("Password is incorrect.")
        return value

    def validate(self, data):
        user = self.context['user']
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        try:
            password_validation.validate_password(data['new_password'], user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return data


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class VaultItemSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = VaultItem
        fields = [
            'id', 'title', 'file', 'recipient', 'is_sent',
            'release_type', 'scheduled_date', 'recurring_interval_days', 'last_sent_at'
        ]
        read_only_fields = ['is_sent', 'last_sent_at']

    def validate(self, data):
        recipient = data.get('recipient', getattr(self.instance, 'recipient', None))
        if recipient is None:
            raise serializers.ValidationError({'recipient': 'Choose a beneficiary.'})
        if recipient.user_id != self.context['request'].user.id:
            raise serializers.ValidationError(
                {'recipient': 'Choose a contact from your Trusted Circle.'}
            )
        if not recipient.roles.filter(
            role='beneficiary',
            consent_status='accepted',
        ).exists():
            raise serializers.ValidationError(
                {'recipient': 'The contact must accept the beneficiary role first.'}
            )

        release_type = data.get('release_type')
        if release_type is None and self.instance:
            release_type = self.instance.release_type

        scheduled_date = data.get(
            'scheduled_date',
            getattr(self.instance, 'scheduled_date', None),
        )
        recurring_interval_days = data.get(
            'recurring_interval_days',
            getattr(self.instance, 'recurring_interval_days', None),
        )

        if release_type == 'scheduled' and not scheduled_date:
            raise serializers.ValidationError(
                {"scheduled_date": "Release Date is Required."}
            )

        if release_type == 'recurring':
            if not scheduled_date:
                raise serializers.ValidationError(
                    {"scheduled_date": "Release Date is Required!"}
                )
            if not recurring_interval_days:
                raise serializers.ValidationError(
                    {"recurring_interval_days": "Recurring release requires interval(days)!"}
                )

        return data

class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data
