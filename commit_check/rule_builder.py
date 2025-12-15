"""Rule builder that creates validation rules from config and catalog."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from commit_check.rules_catalog import COMMIT_RULES, BRANCH_RULES, RuleCatalogEntry
from commit_check import (
    DEFAULT_COMMIT_TYPES,
    DEFAULT_BRANCH_TYPES,
    DEFAULT_BRANCH_NAMES,
    DEFAULT_BOOLEAN_RULES,
)


@dataclass(frozen=True)
class ValidationRule:
    """A complete validation rule with all necessary information."""

    check: str
    regex: Optional[str] = None
    error: Optional[str] = None
    suggest: Optional[str] = None
    value: Any = None
    allowed: Optional[List[str]] = None
    ignored: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        result: Dict[str, Any] = {
            "check": self.check,
            "regex": self.regex or "",
            "error": self.error or "",
            "suggest": self.suggest or "",
        }
        if self.value is not None:
            result["value"] = self.value
        if self.allowed:
            result["allowed"] = self.allowed
            result["allowed_types"] = self.allowed  # Backward compatibility
        if self.ignored:
            result["ignored"] = self.ignored
        return result


class RuleBuilder:
    """Builds validation rules from config and catalog entries."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.commit_config = config.get("commit", {})
        self.branch_config = config.get("branch", {})

    def build_all_rules(self) -> List[ValidationRule]:
        """Build all validation rules from config."""
        rules = []
        rules.extend(self._build_commit_rules())
        rules.extend(self._build_branch_rules())
        return rules

    def _build_commit_rules(self) -> List[ValidationRule]:
        """Build commit-related validation rules."""
        rules = []

        for catalog_entry in COMMIT_RULES:
            rule = self._build_single_rule(catalog_entry, self.commit_config)
            if rule:
                rules.append(rule)

        return rules

    def _build_branch_rules(self) -> List[ValidationRule]:
        """Build branch-related validation rules."""
        rules = []

        for catalog_entry in BRANCH_RULES:
            rule = self._build_single_rule(catalog_entry, self.branch_config)
            if rule:
                rules.append(rule)

        return rules

    def _build_single_rule(
        self, catalog_entry: RuleCatalogEntry, section_config: Dict[str, Any]
    ) -> Optional[ValidationRule]:
        """Build a single validation rule from catalog entry and config."""
        check = catalog_entry.check

        # Handle special cases that need custom logic
        if check == "message":
            return self._build_conventional_commit_rule(catalog_entry)
        elif check == "branch":
            return self._build_conventional_branch_rule(catalog_entry)
        elif check == "subject_max_length":
            return self._build_length_rule(catalog_entry, "subject_max_length")
        elif check == "subject_min_length":
            return self._build_length_rule(catalog_entry, "subject_min_length")
        elif check == "ignore_authors":
            return self._build_author_list_rule(catalog_entry, "ignore_authors")
        elif check == "merge_base":
            return self._build_merge_base_rule(catalog_entry)
        else:
            return self._build_boolean_rule(catalog_entry, section_config)

    def _build_conventional_commit_rule(
        self, catalog_entry: RuleCatalogEntry
    ) -> Optional[ValidationRule]:
        """Build conventional commit message rule."""
        if not self.commit_config.get("conventional_commits", True):
            return None

        allowed_types = self._get_allowed_commit_types()
        regex = self._build_conventional_commit_regex(allowed_types)

        return ValidationRule(
            check=catalog_entry.check,
            regex=regex,
            error=catalog_entry.error,
            suggest=catalog_entry.suggest,
            allowed=allowed_types,
        )

    def _build_conventional_branch_rule(
        self, catalog_entry: RuleCatalogEntry
    ) -> Optional[ValidationRule]:
        """Build conventional branch naming rule."""
        if not self.branch_config.get("conventional_branch", True):
            return None

        allowed_types = self._get_allowed_branch_types()
        allowed_names = self._get_allowed_branch_names()
        regex = self._build_conventional_branch_regex(allowed_types, allowed_names)

        return ValidationRule(
            check=catalog_entry.check,
            regex=regex,
            error=catalog_entry.error,
            suggest=catalog_entry.suggest,
            allowed=allowed_types,
        )

    def _build_length_rule(
        self, catalog_entry: RuleCatalogEntry, config_key: str
    ) -> Optional[ValidationRule]:
        """Build subject length validation rule."""
        length = self.commit_config.get(config_key)
        if not isinstance(length, int):
            return None

        error = (
            catalog_entry.error.format(max_len=length, min_len=length)
            if catalog_entry.error
            else None
        )

        return ValidationRule(
            check=catalog_entry.check,
            error=error,
            suggest=catalog_entry.suggest,
            value=length,
        )

    def _build_author_list_rule(
        self, catalog_entry: RuleCatalogEntry, config_key: str
    ) -> Optional[ValidationRule]:
        """Build author allow/ignore list rule."""
        author_list = self.commit_config.get(config_key)
        if not isinstance(author_list, list) or not author_list:
            return None

        if config_key == "ignore_authors":
            return ValidationRule(check=catalog_entry.check, ignored=author_list)
        return None

    def _build_merge_base_rule(
        self, catalog_entry: RuleCatalogEntry
    ) -> Optional[ValidationRule]:
        """Build merge base validation rule."""
        target = self.branch_config.get("require_rebase_target")
        if not isinstance(target, str) or not target:
            return None

        return ValidationRule(
            check=catalog_entry.check,
            regex=target,
            error=catalog_entry.error,
            suggest=catalog_entry.suggest,
        )

    def _build_boolean_rule(
        self, catalog_entry: RuleCatalogEntry, section_config: Dict[str, Any]
    ) -> Optional[ValidationRule]:
        """Build boolean-based validation rule."""
        check = catalog_entry.check

        default_value = DEFAULT_BOOLEAN_RULES.get(check, True)
        config_value = section_config.get(check, default_value)

        # For "allow_*" rules, only create rule if they're disabled (False)
        # For "require_*" rules, only create rule if they're enabled (True)
        if check.startswith("allow_") and config_value is True:
            return None
        elif check.startswith("require_") and config_value is False:
            return None
        elif (
            check in ["subject_capitalized", "subject_imperative"]
            and config_value is False
        ):
            return None

        return ValidationRule(
            check=catalog_entry.check,
            regex=catalog_entry.regex,
            error=catalog_entry.error,
            suggest=catalog_entry.suggest,
            value=config_value,
        )

    def _get_allowed_commit_types(self) -> List[str]:
        """Get deduplicated list of allowed commit types."""
        types = self.commit_config.get("allow_commit_types", DEFAULT_COMMIT_TYPES)
        return list(dict.fromkeys(types))  # Preserve order, remove duplicates

    def _get_allowed_branch_types(self) -> List[str]:
        """Get deduplicated list of allowed branch types."""
        types = self.branch_config.get("allow_branch_types", DEFAULT_BRANCH_TYPES)
        return list(dict.fromkeys(types))  # Preserve order, remove duplicates

    def _get_allowed_branch_names(self) -> List[str]:
        """Get deduplicated list of allowed branch names."""
        names = self.branch_config.get("allow_branch_names", DEFAULT_BRANCH_NAMES)
        return list(dict.fromkeys(names))  # Preserve order, remove duplicates

    def _build_conventional_commit_regex(self, allowed_types: List[str]) -> str:
        """Build regex for conventional commit messages."""
        types_pattern = "|".join(sorted(set(allowed_types)))
        return rf"^({types_pattern}){{1}}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)|(Merge).*|(fixup!.*)"

    def _build_conventional_branch_regex(
        self, allowed_types: List[str], allowed_names: List[str]
    ) -> str:
        """Build regex for conventional branch names."""
        types_pattern = "|".join(allowed_types)
        # Build pattern for additional allowed branch names
        base_names = ["master", "main", "HEAD", "PR-.+"]
        all_names = base_names + allowed_names
        names_pattern = ")|(".join(all_names)
        return rf"^({types_pattern})\/.+|({names_pattern})"
