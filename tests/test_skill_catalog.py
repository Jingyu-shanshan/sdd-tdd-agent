from pathlib import Path

import pytest

from sdd_tdd_agent.skill_catalog import SkillCatalog


def _skill(path: Path, name: str, description: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n",
        encoding="utf-8",
    )


def test_should_discover_frontmatter_and_prefer_project_skill(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    _skill(
        home / ".agents" / "skills" / "review" / "SKILL.md",
        "review",
        "User review.",
        "USER BODY",
    )
    project_path = project / ".agents" / "skills" / "review" / "SKILL.md"
    _skill(project_path, "review", "Project review.", "PROJECT BODY")

    catalog = SkillCatalog(project, home)
    summaries = catalog.list()
    loaded = catalog.load("review")

    assert [(item.name, item.description, item.source) for item in summaries] == [
        ("review", "Project review.", "project")
    ]
    assert loaded.content.endswith("PROJECT BODY\n")
    assert loaded.path == project_path


def test_should_reject_skill_changed_after_discovery(tmp_path: Path) -> None:
    path = tmp_path / ".agents" / "skills" / "review" / "SKILL.md"
    _skill(path, "review", "Review.", "ORIGINAL")
    catalog = SkillCatalog(tmp_path, tmp_path / "home")
    assert catalog.list()
    _skill(path, "review", "Review.", "CHANGED")

    with pytest.raises(ValueError, match="changed before loading"):
        catalog.load("review")


def test_should_reject_symlinked_skill(tmp_path: Path) -> None:
    external = tmp_path / "external.md"
    external.write_text("---\nname: bad\ndescription: bad\n---\n", encoding="utf-8")
    skill = tmp_path / ".agents" / "skills" / "bad" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.symlink_to(external)

    assert SkillCatalog(tmp_path, tmp_path / "home").list() == ()
