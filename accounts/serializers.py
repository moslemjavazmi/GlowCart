
import binascii

from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils.encoding import force_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode

from rest_framework import serializers

from accounts.models import User
from accounts.services.email_verification import verify_email_code
from accounts.services.token_service import revoke_user_refresh_tokens


User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )

    password_confirm = serializers.CharField(
        write_only=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
        ]
        read_only_fields = ["id"]

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match."
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        try:
            with transaction.atomic():
                return User.objects.create_user(
                    password=password,
                    **validated_data,
                )

        except IntegrityError:
            raise serializers.ValidationError({
                "email": "An account with this email already exists."
            })


class VerifyEmailSerializer(serializers.Serializer):

    email = serializers.EmailField()

    code = serializers.RegexField(
        regex=r"^\d{6}$",
        error_messages={
            "invalid": "Verification code must contain 6 digits."
        },
    )

    def validate(self, attrs):
        email = attrs["email"].strip().lower()

        user = User.objects.filter(
            email__iexact=email
        ).first()

        if user is None:
            raise serializers.ValidationError({
                "email": "Invalid email or verification code."
            })

        if user.is_email_verified:
            raise serializers.ValidationError({
                "email": "Email is already verified."
            })

        attrs["user"] = user
        return attrs


class ResendVerificationSerializer(serializers.Serializer):

    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class LoginSerializer(serializers.Serializer):

    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        email = attrs["email"].strip().lower()

        user = authenticate(
            request=self.context.get("request"),
            username=email,
            password=attrs["password"],
        )

        if user is None:
            raise serializers.ValidationError(
                "Invalid email or password."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This account is inactive."
            )

        if not user.is_email_verified:
            raise serializers.ValidationError(
                "Please verify your email first."
            )

        attrs["user"] = user
        return attrs


class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = User

        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_email_verified",
            "date_joined",
        ]

        read_only_fields = [
            "id",
            "email",
            "role",
            "is_email_verified",
            "date_joined",
        ]


class ChangePasswordSerializer(serializers.Serializer):

    current_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({
                "current_password": "Current password is incorrect."
            })

        if attrs["new_password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match."
            })

        if user.check_password(attrs["new_password"]):
            raise serializers.ValidationError({
                "new_password": "New password must be different."
            })

        validate_password(attrs["new_password"], user=user)

        return attrs

    def save(self, **kwargs):
        from django.contrib.auth import get_user_model

        UserModel = get_user_model()

        with transaction.atomic():
            user = UserModel.objects.select_for_update().get(
                pk=self.context["request"].user.pk
            )

            if not user.check_password(
                self.validated_data["current_password"]
            ):
                raise serializers.ValidationError({
                    "current_password": "Current password is incorrect."
                })

            user.set_password(
                self.validated_data["new_password"]
            )

            user.save(update_fields=["password"])

            revoke_user_refresh_tokens(user)

        return user


class ForgotPasswordSerializer(serializers.Serializer):

    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class ResetPasswordSerializer(serializers.Serializer):

    uid = serializers.CharField()
    token = serializers.CharField()

    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):

        try:
            user_id = force_str(
                urlsafe_base64_decode(attrs["uid"])
            )

            user = User.objects.get(pk=user_id)

        except (
            ValueError,
            TypeError,
            OverflowError,
            binascii.Error,
            DjangoUnicodeDecodeError,
            User.DoesNotExist,
        ):
            raise serializers.ValidationError({
                "uid": "Invalid reset link."
            })

        if not user.is_active:
            raise serializers.ValidationError({
                "uid": "Invalid reset link."
            })

        if not default_token_generator.check_token(
            user,
            attrs["token"],
        ):
            raise serializers.ValidationError({
                "token": "Invalid or expired reset token."
            })

        if attrs["new_password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({
                "password_confirm": "Passwords do not match."
            })

        if user.check_password(attrs["new_password"]):
            raise serializers.ValidationError({
                "new_password": "New password must be different."
            })

        validate_password(
            attrs["new_password"],
            user=user,
        )

        attrs["user"] = user

        return attrs

    def save(self, **kwargs):
        with transaction.atomic():

            user = User.objects.select_for_update().get(
                pk=self.validated_data["user"].pk
            )

            # Recheck token inside the transaction.
            if not default_token_generator.check_token(
                user,
                self.validated_data["token"],
            ):
                raise serializers.ValidationError({
                    "token": "Invalid or expired reset token."
                })

            user.set_password(
                self.validated_data["new_password"]
            )

            user.save(update_fields=["password"])

            revoke_user_refresh_tokens(user)

        return user
