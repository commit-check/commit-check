"""Configuration merger that combines CLI args, env vars, TOML config, and defaults."""

from __future__ import annotations

import argparse
import difflib
import os
from collections.abc import Callable
from typing import Any, ClassVar

from commit_check import (
    DEFAULT_AI_ATTRIBUTION,
    DEFAULT_AI_DISCLOSURE_PATTERN,
    DEFAULT_AI_DISCLOSURE_TRAILERS,
    DEFAULT_BOOLEAN_RULES,
    DEFAULT_BRANCH_NAMES,
    DEFAULT_BRANCH_TYPES,
    DEFAULT_COMMIT_TYPES,
    DEFAULT_PUSH_RULES,
    DEFAULT_TAG_REGEX,
)
from commit_check.config import deep_merge, report_notice
from commit_check.config import load_config as load_toml_config


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


def parse_list(value: Any) -> list[str]:
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


def get_default_config() -> dict[str, Any]:
    """Get the default configuration with all options."""
    return {
        "commit": {
            "conventional_commits": True,
            "message_pattern": "",
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
            "body_max_line_length": 0,
            "require_signed_off_by": DEFAULT_BOOLEAN_RULES["require_signed_off_by"],
            "ignore_authors": [],
            "ai_attribution": DEFAULT_AI_ATTRIBUTION,
            "ai_disclosure_trailers": DEFAULT_AI_DISCLOSURE_TRAILERS.copy(),
            "ai_disclosure_pattern": DEFAULT_AI_DISCLOSURE_PATTERN,
            "author_email_pattern": "^.+@.+$",
            "author_name_pattern": "",
        },
        "branch": {
            "conventional_branch": True,
            "require_description_grammar": False,
            "allow_branch_types": DEFAULT_BRANCH_TYPES.copy(),
            "allow_branch_names": DEFAULT_BRANCH_NAMES.copy(),
            "require_rebase_target": "",
            "ignore_authors": [],
        },
        "push": {
            "allow_force_push": DEFAULT_PUSH_RULES["allow_force_push"],
        },
        "tag": {
            "regex": DEFAULT_TAG_REGEX,
        },
        "files": {
            "max_size": "",
            "prohibited_patterns": [],
            "max_path_length": 0,
        },
        "agent_config": {
            "enabled": False,
            "allowed_mcp_servers": [],
            "allowed_api_endpoints": [],
        },
    }


#: Read from the same file, but not as defaults: ``warn`` and
#: ``[pull_request] ai_declaration_checkboxes`` by the rule builder, ``[jira]`` and
#: the rest of ``[pull_request]`` by the GitHub App.
_OTHER_KEYS = frozenset({"warn", "jira", "pull_request"})

#: Of those, the ones whose contents are not checked here: ``warn`` is a
#: list the rule builder checks itself, and ``[jira]`` is the GitHub App's.
_UNCHECKED_KEYS = frozenset({"warn", "jira"})

#: Keys read from a table besides its defaults. In ``[commit]``,
#: ``require_verified`` is read only by the GitHub App, which has GitHub's
#: verdict on a commit's signature. ``[pull_request]`` has no defaults: the
#: rule builder reads ``ai_declaration_checkboxes`` and the GitHub App the
#: other three, so any other key in it is read by nothing.
_OTHER_SETTINGS: dict[str, frozenset[str]] = {
    "commit": frozenset({"require_verified"}),
    "pull_request": frozenset(
        {"check", "ai_label", "body_ai_attribution", "ai_declaration_checkboxes"}
    ),
}


def _unknown_settings(config: dict[str, Any]) -> list[tuple[str, str]]:
    """``(setting, message)`` for each setting in a config file that nothing reads.

    *setting* is the name as the message shows it, ``[section] key`` or
    ``[section]``.
    """
    defaults = get_default_config()
    names = []
    for section, value in config.items():
        if section in _UNCHECKED_KEYS:
            continue
        if section not in defaults and section not in _OTHER_KEYS:
            names.append((f"[{section}]", section, [*defaults, *_OTHER_KEYS]))
        elif isinstance(value, dict):
            other = _OTHER_SETTINGS.get(section, frozenset())
            # A misspelt key is matched against the defaults, as before,
            # or, in a table that has none, against the keys it can hold.
            candidates = defaults.get(section, other)
            names.extend(
                (f"[{section}] {key}", key, candidates)
                for key in value
                if key not in defaults.get(section, ()) and key not in other
            )
    found = []
    for shown, name, known in names:
        match = difflib.get_close_matches(name, list(known), n=1)
        hint = f"; did you mean {match[0]}?" if match else ""
        found.append((shown, f"unknown setting {shown} is ignored{hint}"))
    return found


def unknown_setting_warnings(config: dict[str, Any]) -> list[str]:
    """One line per setting in a config file that nothing reads.

    A misspelt key used to be ignored in silence, leaving its rule off.
    """
    return [f"⚠ {message}" for _setting, message in _unknown_settings(config)]


class ConfigMerger:
    """Merges configurations from multiple sources with priority: CLI > Env > TOML > Defaults."""

    # Mapping of environment variable names to config keys
    ENV_VAR_MAPPING: ClassVar[dict[str, tuple[str, str, Callable[[Any], Any]]]] = {
        # Commit section
        "CCHK_CONVENTIONAL_COMMITS": ("commit", "conventional_commits", parse_bool),
        "CCHK_MESSAGE_PATTERN": ("commit", "message_pattern", str),
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
        "CCHK_BODY_MAX_LINE_LENGTH": ("commit", "body_max_line_length", parse_int),
        "CCHK_REQUIRE_SIGNED_OFF_BY": ("commit", "require_signed_off_by", parse_bool),
        "CCHK_IGNORE_AUTHORS": ("commit", "ignore_authors", parse_list),
        "CCHK_AI_ATTRIBUTION": ("commit", "ai_attribution", str),
        "CCHK_AI_DISCLOSURE_TRAILERS": (
            "commit",
            "ai_disclosure_trailers",
            parse_list,
        ),
        "CCHK_AI_DISCLOSURE_PATTERN": ("commit", "ai_disclosure_pattern", str),
        "CCHK_AUTHOR_EMAIL_PATTERN": ("commit", "author_email_pattern", str),
        "CCHK_AUTHOR_NAME_PATTERN": ("commit", "author_name_pattern", str),
        # Branch section
        "CCHK_CONVENTIONAL_BRANCH": ("branch", "conventional_branch", parse_bool),
        "CCHK_REQUIRE_DESCRIPTION_GRAMMAR": (
            "branch",
            "require_description_grammar",
            parse_bool,
        ),
        "CCHK_ALLOW_BRANCH_TYPES": ("branch", "allow_branch_types", parse_list),
        "CCHK_ALLOW_BRANCH_NAMES": ("branch", "allow_branch_names", parse_list),
        "CCHK_REQUIRE_REBASE_TARGET": ("branch", "require_rebase_target", str),
        "CCHK_BRANCH_IGNORE_AUTHORS": ("branch", "ignore_authors", parse_list),
        # Push section
        "CCHK_ALLOW_FORCE_PUSH": ("push", "allow_force_push", parse_bool),
        # Tag section
        "CCHK_TAG_REGEX": ("tag", "regex", str),
        # Files section
        "CCHK_FILES_MAX_SIZE": ("files", "max_size", str),
        "CCHK_FILES_PROHIBITED_PATTERNS": ("files", "prohibited_patterns", parse_list),
        "CCHK_FILES_MAX_PATH_LENGTH": ("files", "max_path_length", parse_int),
        # Agent config section
        "CCHK_AGENT_CONFIG_ENABLED": ("agent_config", "enabled", parse_bool),
        "CCHK_AGENT_CONFIG_ALLOWED_MCP_SERVERS": (
            "agent_config",
            "allowed_mcp_servers",
            parse_list,
        ),
        "CCHK_AGENT_CONFIG_ALLOWED_API_ENDPOINTS": (
            "agent_config",
            "allowed_api_endpoints",
            parse_list,
        ),
    }

    # Mapping of CLI argument names to config keys
    CLI_ARG_MAPPING: ClassVar[dict[str, tuple[str, str]]] = {
        # Commit section
        "conventional_commits": ("commit", "conventional_commits"),
        "subject_capitalized": ("commit", "subject_capitalized"),
        "subject_imperative": ("commit", "subject_imperative"),
        "subject_max_length": ("commit", "subject_max_length"),
        "subject_min_length": ("commit", "subject_min_length"),
        "allow_commit_types": ("commit", "allow_commit_types"),
        "allow_merge_commits": ("commit", "allow_merge_commits"),
        "allow_revert_commits": ("commit", "allow_revert_commits"),
        "allow_empty_commits": ("commit", "allow_empty_commits"),
        "allow_fixup_commits": ("commit", "allow_fixup_commits"),
        "allow_wip_commits": ("commit", "allow_wip_commits"),
        "require_body": ("commit", "require_body"),
        "body_max_line_length": ("commit", "body_max_line_length"),
        "require_signed_off_by": ("commit", "require_signed_off_by"),
        "ignore_authors": ("commit", "ignore_authors"),
        "ai_attribution": ("commit", "ai_attribution"),
        "ai_disclosure_trailers": ("commit", "ai_disclosure_trailers"),
        "ai_disclosure_pattern": ("commit", "ai_disclosure_pattern"),
        "author_email_pattern": ("commit", "author_email_pattern"),
        "author_name_pattern": ("commit", "author_name_pattern"),
        # Branch section
        "conventional_branch": ("branch", "conventional_branch"),
        "require_description_grammar": ("branch", "require_description_grammar"),
        "allow_branch_types": ("branch", "allow_branch_types"),
        "allow_branch_names": ("branch", "allow_branch_names"),
        "require_rebase_target": ("branch", "require_rebase_target"),
        "branch_ignore_authors": ("branch", "ignore_authors"),
        # Push section
        "allow_force_push": ("push", "allow_force_push"),
        # Tag section
        "tag_regex": ("tag", "regex"),
        # Files section
        "files_max_size": ("files", "max_size"),
        "files_prohibited_patterns": ("files", "prohibited_patterns"),
        "files_max_path_length": ("files", "max_path_length"),
        # Agent config section
        "agent_config_enabled": ("agent_config", "enabled"),
        "agent_config_allowed_mcp_servers": ("agent_config", "allowed_mcp_servers"),
        "agent_config_allowed_api_endpoints": (
            "agent_config",
            "allowed_api_endpoints",
        ),
    }

    @staticmethod
    def parse_env_vars(notices: list[dict[str, str]] | None = None) -> dict[str, Any]:
        """Parse environment variables with CCHK_ prefix into config dict.

        :param notices: Where to add a notice for a value that cannot be
            parsed, as well as printing it; see
            :func:`~commit_check.config.report_notice`.
        """
        config: dict[str, Any] = {
            "commit": {},
            "branch": {},
            "push": {},
            "tag": {},
            "files": {},
            "agent_config": {},
        }

        for env_var, (section, key, parser) in ConfigMerger.ENV_VAR_MAPPING.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    parsed_value = parser(value)
                    config[section][key] = parsed_value
                except (ValueError, TypeError) as e:
                    # Log warning but don't fail - just skip invalid env vars.
                    # stderr, so --format json output stays parseable.
                    report_notice(
                        notices,
                        env_var,
                        f"Invalid value for {env_var}: {e}",
                        mark="Warning:",
                    )

        # Remove empty sections
        config = {k: v for k, v in config.items() if v}
        return config

    @staticmethod
    def parse_cli_args(args: argparse.Namespace) -> dict[str, Any]:
        """Parse CLI arguments into config dict."""
        config: dict[str, Any] = {
            "commit": {},
            "branch": {},
            "push": {},
            "tag": {},
            "files": {},
            "agent_config": {},
        }

        for arg_name, (section, key) in ConfigMerger.CLI_ARG_MAPPING.items():
            if hasattr(args, arg_name):
                value = getattr(args, arg_name)
                if value is not None:
                    config[section][key] = value

        # Remove empty sections
        config = {k: v for k, v in config.items() if v}
        return config

    @staticmethod
    def from_all_sources(
        cli_args: argparse.Namespace,
        config_path: str | None = None,
        notices: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Merge configs from all sources with priority: CLI > Env > TOML > Defaults.

        Args:
            cli_args: Parsed command line arguments
            config_path: Optional path to TOML config file
            notices: Where to add a notice for each setting that is not in
                force (an ``inherit_from`` not followed, an unknown setting,
                a ``CCHK_*`` value that cannot be parsed), as well as
                printing it; see :func:`~commit_check.config.report_notice`.

        Returns:
            Merged configuration dictionary
        """
        # 1. Start with defaults
        config = get_default_config()

        # 2. Merge TOML config (if exists)
        try:
            toml_config = load_toml_config(config_path or "", notices=notices)
            if toml_config:
                for setting, message in _unknown_settings(toml_config):
                    report_notice(notices, setting, message, mark="⚠")
                deep_merge(config, toml_config)
        except FileNotFoundError:
            # If a specific path was provided and not found, this error is already raised
            # If no path provided and no default files exist, that's fine
            if config_path:
                raise

        # 3. Merge environment variables
        env_config = ConfigMerger.parse_env_vars(notices)
        if env_config:
            deep_merge(config, env_config)

        # 4. Merge CLI arguments (highest priority)
        cli_config = ConfigMerger.parse_cli_args(cli_args)
        if cli_config:
            deep_merge(config, cli_config)

        return config
