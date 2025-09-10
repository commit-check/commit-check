"""The commit-check package's base module."""
from importlib.metadata import version
from commit_check.rules import default_checks as _default_checks

# Exit codes used across the package
PASS = 0
FAIL = 1

# ANSI color codes used for CLI output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET_COLOR = "\033[0m"

DEFAULT_CONFIG = { 'checks': _default_checks() }
CONFIG_FILE = '.'  # Search current directory for commit-check.toml or cchk.toml
__version__ = version("commit-check")
