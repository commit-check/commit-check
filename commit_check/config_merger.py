"""Configuration merger that combines CLI args, env vars, TOML config, and defaults."""

from __future__ import annotations
import os
import argparse
from typing import Dict, Any, Optional, List, Callable, Tuple

from commit_check.config import load_config as load_toml_config
from commit_check import (
    DEFAULT_COMMIT_TYPES,
    DEFAULT_BRANCH_TYPES,
    DEFAULT_BRANCH_NAMES,
    DEFAULT_BOOLEAN_RULES,
)


def parse_bool(value: Any) -> bool:
    """Parse a boolean value from string, int, or bool.

    Accepts: true/false, yes/no, 1/0, t/f, y/n (case-insensitive)
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.lower().strip()
        if normalized in ("true", "yes", "1", "t", "y"):
            return True
        if normalized in ("false", "no", "0", "f", "n"):
            return False
        raise ValueError(f"Cannot parse '{value}' as boolean")
    raise TypeError(f"Cannot convert {type(value).__name__} to bool")


def parse_list(value: Any) -> List[str]:
    """Parse a list from comma-separated string or list."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        # Split by comma and strip whitespace
        return [item.strip() for item in value.split(",") if item.strip()]
    raise TypeError(f"Cannot convert {type(value).__name__} to list")


def parse_int(value: Any) -> int:
    """Parse an integer value."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            raise ValueError(f"Cannot parse '{value}' as integer")
    raise TypeError(f"Cannot convert {type(value).__name__} to int")


def get_default_config() -> Dict[str, Any]:
    """Get the default configuration with all options."""
    return {
        "commit": {
            "conventional_commits": True,
            "subject_capitalized": DEFAULT_BOOLEAN_RULES["subject_capitalized"],
            "subject_imperative": DEFAULT_BOOLEAN_RULES["subject_imperative"],
            "subject_max_length": 80,
            "subject_min_length": 5,
            "allow_commit_types": DEFAULT_COMMIT_TYPES.copy(),
            "allow_merge_commits": DEFAULT_BOOLEAN_RULES["allow_merge_commits"],
            "allow_revert_commits": DEFAULT_BOOLEAN_RULES["allow_revert_commits"],
            "allow_empty_commits": DEFAULT_BOOLEAN_RULES["allow_empty_commits"],
            "allow_fixup_commits": DEFAULT_BOOLEAN_RULES["allow_fixup_commits"],
            "allow_wip_commits": DEFAULT_BOOLEAN_RULES["allow_wip_commits"],
            "require_body": DEFAULT_BOOLEAN_RULES["require_body"],
            "require_signed_off_by": DEFAULT_BOOLEAN_RULES["require_signed_off_by"],
            "ignore_authors": [],
        },
        "branch": {
            "conventional_branch": True,
            "allow_branch_types": DEFAULT_BRANCH_TYPES.copy(),
            "allow_branch_names": DEFAULT_BRANCH_NAMES.copy(),
            "require_rebase_target": "",
            "ignore_authors": [],
        },
    }


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """Deep merge override into base dictionary (modifies base in-place)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value


class ConfigMerger:
    """Merges configurations from multiple sources with priority: CLI > Env > TOML > Defaults."""

    # Mapping of environment variable names to config keys
    ENV_VAR_MAPPING: Dict[str, Tuple[str, str, Callable[[Any], Any]]] = {
        # Commit section
        "CCHK_CONVENTIONAL_COMMITS": ("commit", "conventional_commits", parse_bool),
        "CCHK_SUBJECT_CAPITALIZED": ("commit", "subject_capitalized", parse_bool),
        "CCHK_SUBJECT_IMPERATIVE": ("commit", "subject_imperative", parse_bool),
        "CCHK_SUBJECT_MAX_LENGTH": ("commit", "subject_max_length", parse_int),
        "CCHK_SUBJECT_MIN_LENGTH": ("commit", "subject_min_length", parse_int),
        "CCHK_ALLOW_COMMIT_TYPES": ("commit", "allow_commit_types", parse_list),
        "CCHK_ALLOW_MERGE_COMMITS": ("commit", "allow_merge_commits", parse_bool),
        "CCHK_ALLOW_REVERT_COMMITS": ("commit", "allow_revert_commits", parse_bool),
        "CCHK_ALLOW_EMPTY_COMMITS": ("commit", "allow_empty_commits", parse_bool),
        "CCHK_ALLOW_FIXUP_COMMITS": ("commit", "allow_fixup_commits", parse_bool),
        "CCHK_ALLOW_WIP_COMMITS": ("commit", "allow_wip_commits", parse_bool),
        "CCHK_REQUIRE_BODY": ("commit", "require_body", parse_bool),
        "CCHK_REQUIRE_SIGNED_OFF_BY": ("commit", "require_signed_off_by", parse_bool),
        "CCHK_IGNORE_AUTHORS": ("commit", "ignore_authors", parse_list),
        # Branch section
        "CCHK_CONVENTIONAL_BRANCH": ("branch", "conventional_branch", parse_bool),
        "CCHK_ALLOW_BRANCH_TYPES": ("branch", "allow_branch_types", parse_list),
        "CCHK_ALLOW_BRANCH_NAMES": ("branch", "allow_branch_names", parse_list),
        "CCHK_REQUIRE_REBASE_TARGET": ("branch", "require_rebase_target", str),
        "CCHK_BRANCH_IGNORE_AUTHORS": ("branch", "ignore_authors", parse_list),
    }

    @staticmethod
    def parse_env_vars() -> Dict[str, Any]:
        """Parse environment variables with CCHK_ prefix into config dict."""
        config: Dict[str, Any] = {"commit": {}, "branch": {}}

        for env_var, (section, key, parser) in ConfigMerger.ENV_VAR_MAPPING.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    parsed_value = parser(value)
                    config[section][key] = parsed_value
                except (ValueError, TypeError) as e:
                    # Log warning but don't fail - just skip invalid env vars
                    print(f"Warning: Invalid value for {env_var}: {e}")

        # Remove empty sections
        config = {k: v for k, v in config.items() if v}
        return config

    @staticmethod
    def parse_cli_args(args: argparse.Namespace) -> Dict[str, Any]:
        """Parse CLI arguments into config dict."""
        config: Dict[str, Any] = {"commit": {}, "branch": {}}

        # Commit section arguments
        if (
            hasattr(args, "conventional_commits")
            and args.conventional_commits is not None
        ):
            config["commit"]["conventional_commits"] = args.conventional_commits
        if (
            hasattr(args, "subject_capitalized")
            and args.subject_capitalized is not None
        ):
            config["commit"]["subject_capitalized"] = args.subject_capitalized
        if hasattr(args, "subject_imperative") and args.subject_imperative is not None:
            config["commit"]["subject_imperative"] = args.subject_imperative
        if hasattr(args, "subject_max_length") and args.subject_max_length is not None:
            config["commit"]["subject_max_length"] = args.subject_max_length
        if hasattr(args, "subject_min_length") and args.subject_min_length is not None:
            config["commit"]["subject_min_length"] = args.subject_min_length
        if hasattr(args, "allow_commit_types") and args.allow_commit_types is not None:
            config["commit"]["allow_commit_types"] = args.allow_commit_types
        if (
            hasattr(args, "allow_merge_commits")
            and args.allow_merge_commits is not None
        ):
            config["commit"]["allow_merge_commits"] = args.allow_merge_commits
        if (
            hasattr(args, "allow_revert_commits")
            and args.allow_revert_commits is not None
        ):
            config["commit"]["allow_revert_commits"] = args.allow_revert_commits
        if (
            hasattr(args, "allow_empty_commits")
            and args.allow_empty_commits is not None
        ):
            config["commit"]["allow_empty_commits"] = args.allow_empty_commits
        if (
            hasattr(args, "allow_fixup_commits")
            and args.allow_fixup_commits is not None
        ):
            config["commit"]["allow_fixup_commits"] = args.allow_fixup_commits
        if hasattr(args, "allow_wip_commits") and args.allow_wip_commits is not None:
            config["commit"]["allow_wip_commits"] = args.allow_wip_commits
        if hasattr(args, "require_body") and args.require_body is not None:
            config["commit"]["require_body"] = args.require_body
        if (
            hasattr(args, "require_signed_off_by")
            and args.require_signed_off_by is not None
        ):
            config["commit"]["require_signed_off_by"] = args.require_signed_off_by
        if hasattr(args, "ignore_authors") and args.ignore_authors is not None:
            config["commit"]["ignore_authors"] = args.ignore_authors

        # Branch section arguments
        if (
            hasattr(args, "conventional_branch")
            and args.conventional_branch is not None
        ):
            config["branch"]["conventional_branch"] = args.conventional_branch
        if hasattr(args, "allow_branch_types") and args.allow_branch_types is not None:
            config["branch"]["allow_branch_types"] = args.allow_branch_types
        if hasattr(args, "allow_branch_names") and args.allow_branch_names is not None:
            config["branch"]["allow_branch_names"] = args.allow_branch_names
        if (
            hasattr(args, "require_rebase_target")
            and args.require_rebase_target is not None
        ):
            config["branch"]["require_rebase_target"] = args.require_rebase_target
        if (
            hasattr(args, "branch_ignore_authors")
            and args.branch_ignore_authors is not None
        ):
            config["branch"]["ignore_authors"] = args.branch_ignore_authors

        # Remove empty sections
        config = {k: v for k, v in config.items() if v}
        return config

    @staticmethod
    def from_all_sources(
        cli_args: argparse.Namespace, config_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Merge configs from all sources with priority: CLI > Env > TOML > Defaults.

        Args:
            cli_args: Parsed command line arguments
            config_path: Optional path to TOML config file

        Returns:
            Merged configuration dictionary
        """
        # 1. Start with defaults
        config = get_default_config()

        # 2. Merge TOML config (if exists)
        try:
            toml_config = load_toml_config(config_path or "")
            if toml_config:
                deep_merge(config, toml_config)
        except FileNotFoundError:
            # If a specific path was provided and not found, this error is already raised
            # If no path provided and no default files exist, that's fine
            if config_path:
                raise

        # 3. Merge environment variables
        env_config = ConfigMerger.parse_env_vars()
        if env_config:
            deep_merge(config, env_config)

        # 4. Merge CLI arguments (highest priority)
        cli_config = ConfigMerger.parse_cli_args(cli_args)
        if cli_config:
            deep_merge(config, cli_config)

        return config
