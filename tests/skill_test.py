"""The agent skill in skills/ must stay valid as the CLI changes.

Agents run the commands in SKILL.md as written, so a renamed or removed flag
breaks them silently. These tests fail instead.
"""

import re
from pathlib import Path

import pytest

from commit_check.main import _get_parser

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
SKILL_FILES = sorted(SKILLS_DIR.glob("*/SKILL.md"))


def _frontmatter(text: str) -> dict[str, str]:
    """Top-level ``key: value`` pairs of the YAML frontmatter."""
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "SKILL.md must start with a --- frontmatter block"
    fields = {}
    for line in match.group(1).splitlines():
        if line and not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"')
    return fields


def test_there_is_a_skill():
    assert SKILL_FILES, "no skills/*/SKILL.md found"


@pytest.mark.parametrize("skill", SKILL_FILES, ids=lambda p: p.parent.name)
def test_frontmatter_follows_the_agent_skills_spec(skill):
    """``name`` matches the folder; ``description`` is set and short enough."""
    fields = _frontmatter(skill.read_text(encoding="utf-8"))
    assert fields.get("name") == skill.parent.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fields["name"])
    assert 0 < len(fields.get("description", "")) <= 1024


@pytest.mark.parametrize("skill", SKILL_FILES, ids=lambda p: p.parent.name)
def test_every_flag_in_the_skill_exists(skill):
    """Each ``--flag`` on a ``commit-check`` command line is a real option."""
    known = {
        option for action in _get_parser()._actions for option in action.option_strings
    }
    text = skill.read_text(encoding="utf-8")
    used = {
        flag
        for line in text.splitlines()
        if "commit-check " in line
        for flag in re.findall(r"(?<![\w-])--[a-z][a-z-]*", line)
    }
    assert used, "the skill shows no commit-check command"
    unknown = sorted(used - known)
    assert not unknown, f"flags not in the CLI: {unknown}"
