"""The commit-check package's base module.

Exports:
        PASS / FAIL exit codes
        ANSI color constants
        __version__ (package version)
"""

import os
import sys
from importlib.metadata import version, PackageNotFoundError

# Exit codes used across the package
PASS = 0
FAIL = 1


def supports_color() -> bool:
    """Whether the terminal renders ANSI color.

    A piped or redirected stream is read as plain text (a CI log, a file, an
    agent harness), where the escape sequences are noise, so this errs towards
    saying no when ``stdout`` is not a terminal.

    ``FORCE_COLOR`` overrides everything else, in both directions: ``0`` turns
    color off even on a terminal, any other value turns it on even when piped.
    ``NO_COLOR`` set to any non-empty value turns color off, per the
    convention at https://no-color.org — it is what users export globally, so
    it outranks detection but yields to an explicit force.

    An empty ``TERM`` is the same "no terminal type" signal as ``dumb``: the
    user has deliberately said there are no terminfo capabilities, so emit
    plain text. An *unset* ``TERM`` is different — it just means nobody set
    it, and a real terminal is still likely color-capable.
    """
    forced = os.environ.get("FORCE_COLOR")
    if forced:
        return forced != "0"
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    if os.environ.get("TERM") in ("", "dumb"):
        return False
    return True


# ANSI color codes used for CLI output, empty when stdout cannot render color.
_colored = supports_color()
RED = "\033[91m" if _colored else ""
GREEN = "\033[92m" if _colored else ""
YELLOW = "\033[93m" if _colored else ""
RESET_COLOR = "\033[0m" if _colored else ""

# Follow conventional commits
DEFAULT_COMMIT_TYPES = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "test",
    "chore",
    "perf",
    "build",
    "ci",
]
# Follow conventional branch (https://conventionalbranch.org/)
# Includes AI agent prefixes (spec v1.1.0) and bot prefixes
DEFAULT_BRANCH_TYPES = [
    "feature",
    "bugfix",
    "hotfix",
    "release",
    "chore",
    "feat",
    "fix",
    "build",
    "ci",
    "docs",
    "perf",
    "refactor",
    "test",
    "style",
    # AI agent prefixes (conventional branch spec v1.1.0)
    "ai",
    "claude",
    "codex",
    "copilot",
    "cursor",
    # Automation/bot prefixes
    "dependabot",
    "renovate",
]
# Additional allowed branch names (e.g., develop, staging)
DEFAULT_BRANCH_NAMES: list[str] = []

# Push-related defaults
DEFAULT_PUSH_RULES = {
    "allow_force_push": True,
}

# Handle different default values for different rules
DEFAULT_BOOLEAN_RULES = {
    "subject_capitalized": False,
    "subject_imperative": False,
    "allow_merge_commits": True,
    "allow_revert_commits": True,
    "allow_empty_commits": True,
    "allow_fixup_commits": True,
    "allow_wip_commits": True,
    "require_body": False,
    "require_signed_off_by": False,
}

# AI attribution defaults
DEFAULT_AI_ATTRIBUTION = "ignore"  # "ignore" | "forbid"


try:
    __version__ = version("commit-check")
except PackageNotFoundError:
    __version__ = "0.0.0.dev"
