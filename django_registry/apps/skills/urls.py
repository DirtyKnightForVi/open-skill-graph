from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuditLogViewSet,
    IssueDownloadTokenView,
    ResolveDownloadTokenView,
    SessionSkillBindingViewSet,
    SkillPermissionViewSet,
    SkillVersionViewSet,
    SkillViewSet,
)


router = DefaultRouter()
router.register(r"skills", SkillViewSet, basename="skills")
router.register(r"skill-versions", SkillVersionViewSet, basename="skill-versions")
router.register(r"skill-permissions", SkillPermissionViewSet, basename="skill-permissions")
router.register(r"session-bindings", SessionSkillBindingViewSet, basename="session-bindings")
router.register(r"audit", AuditLogViewSet, basename="audit")

urlpatterns = [
    path("distribution/issue-download-token", IssueDownloadTokenView.as_view(), name="issue-download-token"),
    path("distribution/resolve-download-token", ResolveDownloadTokenView.as_view(), name="resolve-download-token"),
    path("", include(router.urls)),
]
