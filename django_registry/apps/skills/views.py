from datetime import datetime, timedelta, timezone

from django.core import signing
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog, SessionSkillBinding, Skill, SkillPermission, SkillStatus, SkillVersion, SkillVisibility
from .serializers import (
    AuditLogSerializer,
    SessionSkillBindingSerializer,
    SkillPermissionSerializer,
    SkillSerializer,
    SkillVersionSerializer,
)


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all().order_by("-updated_at")
    serializer_class = SkillSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        owner_id = self.request.query_params.get("owner_id")
        visibility = self.request.query_params.get("visibility")
        status_value = self.request.query_params.get("status")
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        if visibility:
            queryset = queryset.filter(visibility=visibility)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset

    @action(detail=False, methods=["get"], url_path="resolve")
    def resolve(self, request):
        owner_id = request.query_params.get("owner_id")
        skill_name = request.query_params.get("skill_name")
        if not owner_id or not skill_name:
            return Response(
                {"message": "owner_id and skill_name are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        skill = Skill.objects.filter(owner_id=owner_id, name=skill_name).first()
        if not skill:
            return Response({"message": "skill not found"}, status=status.HTTP_404_NOT_FOUND)

        version = skill.versions.filter(is_active=True).order_by("-created_at").first()
        if not version:
            version = skill.versions.order_by("-created_at").first()
        if not version:
            return Response({"message": "skill version not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "skill": SkillSerializer(skill).data,
                "version": SkillVersionSerializer(version).data,
            }
        )

    @action(detail=False, methods=["get"], url_path="common")
    def common(self, request):
        skills = Skill.objects.filter(
            visibility__in=[SkillVisibility.COMMON, SkillVisibility.PUBLIC],
            status=SkillStatus.PUBLISHED,
        ).order_by("name")

        data = []
        for skill in skills:
            version = skill.versions.filter(is_active=True).order_by("-created_at").first()
            if not version:
                continue
            data.append(
                {
                    "skill": SkillSerializer(skill).data,
                    "version": SkillVersionSerializer(version).data,
                }
            )
        return Response(data)


class SkillVersionViewSet(viewsets.ModelViewSet):
    queryset = SkillVersion.objects.select_related("skill").all().order_by("-created_at")
    serializer_class = SkillVersionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        skill_id = self.request.query_params.get("skill_id")
        if skill_id:
            queryset = queryset.filter(skill_id=skill_id)
        return queryset

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        current = self.get_object()
        with transaction.atomic():
            SkillVersion.objects.filter(skill=current.skill).exclude(pk=current.pk).update(is_active=False)
            current.is_active = True
            current.save(update_fields=["is_active"])
        return Response(SkillVersionSerializer(current).data)


class SkillPermissionViewSet(viewsets.ModelViewSet):
    queryset = SkillPermission.objects.select_related("skill").all().order_by("-created_at")
    serializer_class = SkillPermissionSerializer


class SessionSkillBindingViewSet(viewsets.ModelViewSet):
    queryset = SessionSkillBinding.objects.select_related("skill_version", "skill_version__skill").all().order_by("-updated_at")
    serializer_class = SessionSkillBindingSerializer


class AuditLogViewSet(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all().order_by("-created_at")
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        trace_id = self.request.query_params.get("trace_id")
        if trace_id:
            queryset = queryset.filter(trace_id=trace_id)
        return queryset


class IssueDownloadTokenView(APIView):
    def post(self, request):
        skill_version_id = request.data.get("skill_version_id")
        ttl_seconds = int(request.data.get("ttl_seconds", 300))
        ttl_seconds = max(60, min(ttl_seconds, 3600))

        skill_version = get_object_or_404(SkillVersion, id=skill_version_id)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        token = signing.dumps(
            {
                "skill_version_id": str(skill_version.id),
                "exp": int(expires_at.timestamp()),
            },
            salt="skills-distribution",
        )

        return Response(
            {
                "token": token,
                "expires_at": expires_at.isoformat(),
                "artifact_uri": skill_version.artifact_uri,
                "artifact_sha256": skill_version.artifact_sha256,
            }
        )


class ResolveDownloadTokenView(APIView):
    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"message": "token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = signing.loads(token, salt="skills-distribution", max_age=3600)
        except signing.BadSignature:
            return Response({"message": "invalid token"}, status=status.HTTP_400_BAD_REQUEST)

        skill_version = get_object_or_404(SkillVersion, id=payload.get("skill_version_id"))
        return Response(
            {
                "skill_version_id": str(skill_version.id),
                "artifact_uri": skill_version.artifact_uri,
                "artifact_sha256": skill_version.artifact_sha256,
            }
        )
