from rest_framework import serializers
from django.contrib.auth import password_validation
from .models import Credentials, Nominee, User, NomineeRole,VaultItem
from django.core.exceptions import ValidationError


class NomineeSerializer(serializers.ModelSerializer):
    roles = serializers.MultipleChoiceField(
        choices=[('witness', 'Death Witness'), ('beneficiary', 'Beneficiary')],
        write_only=True
    )

    class Meta:
        model = Nominee
        fields = ['id', 'nominee_name', 'nominee_email', 'nominee_phone', 'relationship', 'user', 'roles']
        read_only_fields = ['user']

    def create(self, validated_data):
        roles_data = validated_data.pop('roles')
        validated_data['user'] = self.context['request'].user
        nominee = Nominee.objects.create(**validated_data)

        for role in roles_data:
            NomineeRole.objects.create(nominee=nominee, role=role)

        return nominee

    def update(self, instance, validated_data):
        roles_data = validated_data.pop('roles', None)

    
        instance = super().update(instance, validated_data)

        if roles_data is not None:
            existing_roles = set(instance.roles.values_list('role', flat=True))
            new_roles = set(roles_data)

            
            roles_to_remove = existing_roles - new_roles
            instance.roles.filter(role__in=roles_to_remove).delete()

        
            roles_to_add = new_roles - existing_roles
            for role in roles_to_add:
                NomineeRole.objects.create(nominee=instance, role=role)

        return instance

class NomineeRoleSerializer(serializers.ModelSerializer):
        
    nominee_name = serializers.CharField(source='nominee.nominee_name', read_only=True)

    class Meta:
        model = NomineeRole
        fields = ['id', 'role','nominee_name','nominee']
 
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
            'password',             # 👈 Here, The password field was missing...
            'nominee_details',
            'assigned_nominee_id'
        ]                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  # serializers.py
    extra_kwargs = {'password': {'write_only': True}}  


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 
                  'dob', 'gender', 'phone']             

class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.CharField(max_length=15)
    gender = serializers.ChoiceField(choices=['Male', 'Female', 'Other'])
    dob = serializers.DateField(required=False, allow_null=True)

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
            phone=validated_data.get('phone'),
            gender=validated_data.get('gender'),
            dob=validated_data.get('dob'),
        )
        return user

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context['user']  # ← request.user ki jagah yeh
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
    file = serializers.FileField()
    class Meta:
        model = VaultItem
        fields = [
            'id', 'title', 'file', 'recipient', 'is_sent',
            'release_type', 'scheduled_date', 'recurring_interval_days', 'last_sent_at'
        ]
        read_only_fields = ['is_sent', 'last_sent_at']

    def validate(self, data):
        release_type = data.get('release_type')

        if release_type == 'scheduled' and not data.get('scheduled_date'):
            raise serializers.ValidationError(
                {"scheduled_date": "Release Date is Required."}
            )

        if release_type == 'recurring':
            if not data.get('scheduled_date'):
                raise serializers.ValidationError(
                    {"scheduled_date": "Release Date is Required!"}
                )
            if not data.get('recurring_interval_days'):
                    raise serializers.ValidationError(
                    {"recurring_interval_days": "Recurring release requires interval(days)!"}
                  )

        return data    
