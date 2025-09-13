"""The commit-check package's base module.

Exports:
        PASS / FAIL exit codes
        DEFAULT_CONFIG: minimal default rule set used when no config found
        ANSI color constants
        __version__ (package version)
"""

from importlib.metadata import version
from commit_check.rules import build_checks_from_toml as _build_checks_from_toml

# Exit codes used across the package
PASS = 0
FAIL = 1

# ANSI color codes used for CLI output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET_COLOR = "\033[0m"

# Default (empty) configuration translated into internal checks structure
DEFAULT_CONFIG = _build_checks_from_toml({})

CONFIG_FILE = "."  # Search current directory for commit-check.toml or cchk.toml
__version__ = version("commit-check")
