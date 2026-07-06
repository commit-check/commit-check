"""The commit-check package's base module.

Exports:
        PASS / FAIL exit codes
        ANSI color constants
        __version__ (package version)
"""

from importlib.metadata import version

# Exit codes used across the package
PASS = 0
FAIL = 1

# ANSI color codes used for CLI output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET_COLOR = "\033[0m"

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


__version__ = version("commit-check")
