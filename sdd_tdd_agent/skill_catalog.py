import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


MAX_SKILL_BYTES = 256_000
MAX_FRONTMATTER_BYTES = 8_192
SKILL_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


@dataclass(frozen=True)
class SkillSummary:
    """Frontmatter-only metadata for one available Skill."""

    name: str
    description: str
    source: str
    path: Path


@dataclass(frozen=True)
class LoadedSkill:
    """Validated complete Skill content selected by the user."""

    name: str
    content: str
    source: str
    path: Path


@dataclass(frozen=True)
class _SkillEntry:
    summary: SkillSummary
    identity: Tuple[int, int, int, int]


class SkillCatalog:
    """Discover Skill frontmatter and load content only after selection."""

    def __init__(self, root: Path, home: Optional[Path] = None) -> None:
        self._root = root.resolve()
        self._home = (Path.home() if home is None else home).resolve()
        self._entries: Dict[str, _SkillEntry] = {}

    def list(self) -> Tuple[SkillSummary, ...]:
        """List user and project Skills with project precedence."""
        user = self._scan(self._home / ".agents" / "skills", "user")
        project = self._scan(self._root / ".agents" / "skills", "project")
        self._entries = {**user, **project}
        return tuple(self._entries[name].summary for name in sorted(self._entries))

    def load(self, name: str) -> LoadedSkill:
        """Load one selected Skill after size and concurrency checks."""
        if not self._entries:
            self.list()
        try:
            entry = self._entries[name]
        except KeyError as error:
            raise ValueError(f"Unknown Skill: {name}") from error
        path = entry.summary.path
        try:
            if path.is_symlink():
                raise ValueError("Skill path is unsafe")
            before = path.stat()
            if _identity(before) != entry.identity:
                raise ValueError("Skill changed before loading")
            if before.st_size > MAX_SKILL_BYTES:
                raise ValueError("Skill is too large")
            content = path.read_text(encoding="utf-8")
            after = path.stat()
        except UnicodeError as error:
            raise ValueError("Skill is not valid UTF-8") from error
        except ValueError:
            raise
        except OSError as error:
            raise ValueError("Skill could not be read") from error
        if _identity(before) != _identity(after):
            raise ValueError("Skill changed before loading")
        return LoadedSkill(
            entry.summary.name,
            content,
            entry.summary.source,
            path,
        )

    def _scan(self, directory: Path, source: str) -> Dict[str, _SkillEntry]:
        if (
            not directory.is_dir()
            or directory.is_symlink()
            or directory.parent.is_symlink()
        ):
            return {}
        entries: Dict[str, _SkillEntry] = {}
        for child in sorted(directory.iterdir()):
            path = child / "SKILL.md"
            if (
                not child.is_dir()
                or child.is_symlink()
                or not path.is_file()
                or path.is_symlink()
            ):
                continue
            entry = _read_summary(path, source)
            if entry is not None:
                entries[entry.summary.name] = entry
        return entries


def _read_summary(path: Path, source: str) -> Optional[_SkillEntry]:
    try:
        metadata = path.stat()
        if metadata.st_size > MAX_SKILL_BYTES:
            return None
        with path.open("rb") as stream:
            prefix = stream.read(MAX_FRONTMATTER_BYTES)
        text = prefix.decode("utf-8")
    except (OSError, UnicodeError):
        return None
    frontmatter = _frontmatter(text)
    if frontmatter is None:
        return None
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if (
        SKILL_NAME_PATTERN.fullmatch(name) is None
        or not description
        or len(description) > 500
        or any(ord(character) < 32 for character in description)
    ):
        return None
    summary = SkillSummary(name, description, source, path)
    return _SkillEntry(summary, _identity(metadata))


def _frontmatter(value: str) -> Optional[Dict[str, str]]:
    lines = value.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields: Dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        key, separator, content = line.partition(":")
        if separator and key in {"name", "description"}:
            fields[key] = content.strip().strip("\"'")
    return None


def _identity(metadata: object) -> Tuple[int, int, int, int]:
    return (
        int(getattr(metadata, "st_dev")),
        int(getattr(metadata, "st_ino")),
        int(getattr(metadata, "st_size")),
        int(getattr(metadata, "st_mtime_ns")),
    )
