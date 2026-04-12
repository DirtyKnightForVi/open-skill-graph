from django.contrib import admin

from .models import AuditLog, SessionSkillBinding, Skill, SkillPermission, SkillVersion


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("owner_id", "name", "visibility", "status", "updated_at")
    search_fields = ("owner_id", "name", "display_name")
    list_filter = ("visibility", "status")


@admin.register(SkillVersion)
class SkillVersionAdmin(admin.ModelAdmin):
    list_display = ("skill", "version", "is_active", "created_at")
    search_fields = ("skill__owner_id", "skill__name", "version")
    list_filter = ("is_active",)


@admin.register(SkillPermission)
class SkillPermissionAdmin(admin.ModelAdmin):
    list_display = ("skill", "subject_type", "subject_id", "created_at")
    search_fields = ("skill__name", "subject_id")


@admin.register(SessionSkillBinding)
class SessionSkillBindingAdmin(admin.ModelAdmin):
    list_display = ("session_id", "user_id", "skill_version", "status", "updated_at")
    search_fields = ("session_id", "user_id", "skill_version__skill__name")
    list_filter = ("status",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("trace_id", "actor_id", "action", "result", "created_at")
    search_fields = ("trace_id", "actor_id", "action", "target_id")
    list_filter = ("result",)
