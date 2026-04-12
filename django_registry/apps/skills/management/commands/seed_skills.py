import hashlib
import os
import re
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.skills.models import Skill, SkillStatus, SkillVersion, SkillVisibility


class Command(BaseCommand):
    help = "Import skill packages from local storage and seed skill/version records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--storage-path",
            dest="storage_path",
            default=os.getenv("SKILL_STORAGE_PATH", "Agent_Work_Dir/Files/Download_Skills"),
            help="Local storage path that contains SKILL_*.zip files.",
        )
        parser.add_argument(
            "--owner-id",
            dest="owner_id",
            default="common",
            help="Only import this owner when --all-owners is not set.",
        )
        parser.add_argument(
            "--all-owners",
            action="store_true",
            dest="all_owners",
            help="Import all owners found in storage.",
        )
        parser.add_argument(
            "--skill-version",
            dest="skill_version",
            default="1.0.0",
            help="Registry version tag used when creating/updating SkillVersion.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Show what would be changed without writing to DB.",
        )

    def handle(self, *args, **options):
        storage_root = self._resolve_storage_root(options["storage_path"])
        owner_id = options["owner_id"]
        all_owners = bool(options["all_owners"])
        version = options["skill_version"]
        dry_run = bool(options["dry_run"])

        archives = sorted(storage_root.glob("SKILL_*.zip"))
        if not archives:
            self.stdout.write(self.style.WARNING(f"No skill package found under {storage_root}"))
            return

        scanned = 0
        imported = 0
        skipped = 0

        for archive_path in archives:
            scanned += 1
            parsed = self._parse_storage_key(archive_path.stem)
            if not parsed:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"Skip invalid key: {archive_path.stem}"))
                continue

            owner, default_skill_name = parsed
            if not all_owners and owner != owner_id:
                skipped += 1
                continue

            metadata = self._read_skill_metadata(archive_path)
            skill_name = metadata["name"] or default_skill_name
            skill_desc = metadata["description"]
            artifact_sha256 = self._sha256_of_file(archive_path)
            artifact_uri = str(archive_path.resolve())

            visibility = SkillVisibility.COMMON if owner == "common" else SkillVisibility.PRIVATE
            status = SkillStatus.PUBLISHED if owner == "common" else SkillStatus.DRAFT

            if dry_run:
                imported += 1
                self.stdout.write(
                    f"[dry-run] {owner}/{skill_name} -> version={version}, sha256={artifact_sha256[:12]}..."
                )
                continue

            with transaction.atomic():
                skill, _ = Skill.objects.update_or_create(
                    owner_id=owner,
                    name=skill_name,
                    defaults={
                        "display_name": skill_name,
                        "description": skill_desc,
                        "visibility": visibility,
                        "status": status,
                    },
                )

                skill_version, _ = SkillVersion.objects.update_or_create(
                    skill=skill,
                    version=version,
                    defaults={
                        "description": f"Imported from {archive_path.name}",
                        "artifact_uri": artifact_uri,
                        "artifact_sha256": artifact_sha256,
                        "metadata": {
                            "source": "local-storage",
                            "storage_key": archive_path.stem,
                        },
                        "is_active": True,
                    },
                )

                SkillVersion.objects.filter(skill=skill).exclude(pk=skill_version.pk).update(is_active=False)

            imported += 1
            self.stdout.write(self.style.SUCCESS(f"Imported {owner}/{skill_name}:{version}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. scanned={scanned}, imported={imported}, skipped={skipped}, storage={storage_root}"
            )
        )

    @staticmethod
    def _parse_storage_key(storage_key: str):
        if not storage_key.startswith("SKILL_"):
            return None

        suffix = storage_key[len("SKILL_") :]
        if "_" not in suffix:
            return None

        owner, skill_name = suffix.split("_", 1)
        owner = owner.strip()
        skill_name = skill_name.strip()
        if not owner or not skill_name:
            return None

        return owner, skill_name

    @staticmethod
    def _sha256_of_file(file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as fp:
            for chunk in iter(lambda: fp.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _read_skill_metadata(archive_path: Path):
        content = ""
        with zipfile.ZipFile(archive_path, "r") as zip_file:
            names = zip_file.namelist()
            candidate = "SKILL.md"
            if candidate not in names:
                candidate = next((name for name in names if name.endswith("/SKILL.md")), "")
            if candidate:
                content = zip_file.read(candidate).decode("utf-8", errors="ignore")

        if not content:
            return {"name": "", "description": ""}

        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        frontmatter = match.group(1) if match else ""

        name_match = re.search(r"^name:\s*(.+?)$", frontmatter, re.MULTILINE)
        desc_match = re.search(r"^description:\s*(.+?)$", frontmatter, re.MULTILINE)

        return {
            "name": name_match.group(1).strip().strip('"\'') if name_match else "",
            "description": desc_match.group(1).strip().strip('"\'') if desc_match else "",
        }

    @staticmethod
    def _resolve_storage_root(storage_path: str) -> Path:
        raw_path = Path(storage_path)
        if raw_path.is_absolute():
            resolved = raw_path
        else:
            candidates = [
                Path.cwd() / raw_path,
                settings.BASE_DIR.parent / raw_path,
            ]
            resolved = next((item for item in candidates if item.exists()), candidates[0])

        if not resolved.exists():
            raise CommandError(f"Storage path does not exist: {resolved}")

        return resolved
