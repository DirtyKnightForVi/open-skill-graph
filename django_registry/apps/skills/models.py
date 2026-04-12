import uuid

from django.db import models


class SkillVisibility(models.TextChoices):
    PRIVATE = "private", "Private"
    SHARED = "shared", "Shared"
    PUBLIC = "public", "Public"
    COMMON = "common", "Common"


class SkillStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    DEPRECATED = "deprecated", "Deprecated"
    DISABLED = "disabled", "Disabled"


class BindingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    MOUNTED = "mounted", "Mounted"
    FAILED = "failed", "Failed"
    UNMOUNTED = "unmounted", "Unmounted"


class AuditResult(models.TextChoices):
    SUCCESS = "success", "Success"
    FAIL = "fail", "Fail"


class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=128)
    display_name = models.CharField(max_length=128, blank=True, default="")
    description = models.TextField(blank=True, default="")
    visibility = models.CharField(max_length=16, choices=SkillVisibility.choices, default=SkillVisibility.PRIVATE)
    status = models.CharField(max_length=16, choices=SkillStatus.choices, default=SkillStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "skill"
        constraints = [
            models.UniqueConstraint(fields=["owner_id", "name"], name="uq_skill_owner_name"),
        ]
        indexes = [
            models.Index(fields=["owner_id", "visibility", "status"], name="idx_skill_query"),
        ]

    def __str__(self) -> str:
        return f"{self.owner_id}/{self.name}"


class SkillVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=32)
    description = models.TextField(blank=True, default="")
    artifact_uri = models.CharField(max_length=512)
    artifact_sha256 = models.CharField(max_length=128)
    signature = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skill_version"
        constraints = [
            models.UniqueConstraint(fields=["skill", "version"], name="uq_skill_version"),
        ]
        indexes = [
            models.Index(fields=["skill", "is_active"], name="idx_skill_active"),
        ]

    def __str__(self) -> str:
        return f"{self.skill.owner_id}/{self.skill.name}:{self.version}"


class SkillPermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="permissions")
    subject_type = models.CharField(max_length=16)
    subject_id = models.CharField(max_length=128)
    actions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skill_permission"
        constraints = [
            models.UniqueConstraint(
                fields=["skill", "subject_type", "subject_id"],
                name="uq_skill_permission_subject",
            ),
        ]


class SessionSkillBinding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=128)
    user_id = models.CharField(max_length=64)
    skill_version = models.ForeignKey(SkillVersion, on_delete=models.PROTECT, related_name="bindings")
    sandbox_id = models.CharField(max_length=128, blank=True, default="")
    mounted_path = models.CharField(max_length=256)
    status = models.CharField(max_length=16, choices=BindingStatus.choices, default=BindingStatus.PENDING)
    expire_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "session_skill_binding"
        indexes = [
            models.Index(fields=["session_id", "user_id"], name="idx_binding_session_user"),
            models.Index(fields=["status", "expire_at"], name="idx_binding_status_expire"),
        ]


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trace_id = models.CharField(max_length=64, db_index=True)
    actor_id = models.CharField(max_length=64)
    action = models.CharField(max_length=128)
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=128, blank=True, default="")
    result = models.CharField(max_length=16, choices=AuditResult.choices, default=AuditResult.SUCCESS)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        indexes = [
            models.Index(fields=["trace_id", "created_at"], name="idx_audit_trace_time"),
            models.Index(fields=["action", "created_at"], name="idx_audit_action_time"),
        ]
