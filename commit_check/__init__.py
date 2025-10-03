"""The commit-check package's base module.

Exports:
        PASS / FAIL exit codes
        DEFAULT_CONFIG: minimal default rule set used when no config found
        ANSI color constants
        __version__ (package version)
"""

from importlib.metadata import version
from commit_check.rule_builder import RuleBuilder

# Exit codes used across the package
PASS = 0
FAIL = 1

# ANSI color codes used for CLI output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET_COLOR = "\033[0m"

# Default (empty) configuration translated into internal checks structure
_rule_builder = RuleBuilder({})
_default_rules = _rule_builder.build_all_rules()
DEFAULT_CONFIG = {"checks": [rule.to_dict() for rule in _default_rules]}

CONFIG_FILE = "."  # Search current directory for commit-check.toml or cchk.toml
__version__ = version("commit-check")
