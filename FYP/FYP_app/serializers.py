from rest_framework import serializers
from django.contrib.auth import password_validation
from .models import Credentials, Nominee, User
from django.core.exceptions import ValidationError

class NomineeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nominee
        fields = ['id', 'nominee_name', 'nominee_email', 'nominee_phone', 'relationship']

 
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
            'username_on_platform', 
            'email_on_platform',
            'password',             # 👈 Here, The password field was missing...
            'nominee_details',
            'assigned_nominee_id'
        ]    
        # The Reason of adding extra_kwargs={} : This tells Django that the password data should only travel one way—from the user into the database (Write-Only).
        #It acts as an absolute privacy shield.
         extra_kwargs = {
            'password': {'write_only': True}  # ADD THIS LINE FOR SECURITY
        }



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 
                  'dob', 'gender', 'phone']             



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
        user = self.context['user']  # ← yahan bhi
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        try:
            password_validation.validate_password(data['new_password'], user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return data
