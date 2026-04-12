from rest_framework import serializers

from .models import AuditLog, SessionSkillBinding, Skill, SkillPermission, SkillVersion


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = "__all__"


class SkillVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillVersion
        fields = "__all__"


class SkillPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillPermission
        fields = "__all__"


class SessionSkillBindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionSkillBinding
        fields = "__all__"


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"


class SkillResolveResponseSerializer(serializers.Serializer):
    skill = SkillSerializer()
    version = SkillVersionSerializer()
