"""Validation profile discovery for the upload page."""
from pathlib import Path


KNOWN_PROFILE_LABELS: dict[str, str] = {
    "iamcompact-default": "IAM COMPACT Default",
    "new-project-defs": "New Definitions",
}


def _find_repo_root() -> Path:
    for parent in (Path.cwd(), *Path.cwd().parents):
        if (parent / "nomenclatures").is_dir():
            return parent
    return Path.cwd()


def _profile_label(profile_name: str) -> str:
    if profile_name in KNOWN_PROFILE_LABELS:
        return KNOWN_PROFILE_LABELS[profile_name]
    return profile_name.replace("-", " ").replace("_", " ").title()


def get_validation_profiles() -> dict[str, str]:
    """Return available validation profiles as display label -> profile name."""
    nomenclatures_dir = _find_repo_root() / "nomenclatures"
    profile_files = sorted(nomenclatures_dir.glob("*.yaml"))

    profiles = {
        _profile_label(profile_file.stem): profile_file.stem
        for profile_file in profile_files
    }

    if "IAM COMPACT Default" in profiles:
        return {
            "IAM COMPACT Default": profiles.pop("IAM COMPACT Default"),
            **profiles,
        }

    return profiles or {"IAM COMPACT Default": "iamcompact-default"}
