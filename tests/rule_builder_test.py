"""Tests for commit_check.rule_builder module."""

from commit_check.rule_builder import ValidationRule, RuleBuilder
from commit_check.rules_catalog import RuleCatalogEntry
import pytest


class TestValidationRule:
    @pytest.mark.benchmark
    def test_validation_rule_to_dict_with_ignored(self):
        """Test ValidationRule.to_dict() method with ignored field."""
        rule = ValidationRule(check="test_check", ignored=["ignored1", "ignored2"])

        result = rule.to_dict()
        assert result["ignored"] == ["ignored1", "ignored2"]


class TestRuleBuilder:
    @pytest.mark.benchmark
    def test_rule_builder_conventional_commits_disabled(self):
        """Test RuleBuilder when conventional_commits is disabled (line 115)."""
        config = {"commit": {"conventional_commits": False}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="message", regex="", error="", suggest=""
        )

        # This should return None when conventional_commits is False
        rule = builder._build_conventional_commit_rule(catalog_entry)
        assert rule is None

    @pytest.mark.benchmark
    def test_rule_builder_conventional_branch_disabled(self):
        """Test RuleBuilder when conventional_branch is disabled (line 133)."""
        config = {"branch": {"conventional_branch": False}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(check="branch", regex="", error="", suggest="")

        # This should return None when conventional_branch is False
        rule = builder._build_conventional_branch_rule(catalog_entry)
        assert rule is None

    @pytest.mark.benchmark
    def test_rule_builder_ignore_authors_list(self):
        """Test RuleBuilder with ignore_authors list."""
        config = {"commit": {"ignore_authors": ["spam@example.com", "bot@example.com"]}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="ignore_authors",
            regex="",
            error="Author ignored",
            suggest="Use different author",
        )

        # This should create a rule with ignored authors
        rule = builder._build_author_list_rule(catalog_entry, "ignore_authors")
        assert rule is not None
        assert rule.check == "ignore_authors"
        assert rule.ignored == ["spam@example.com", "bot@example.com"]

    @pytest.mark.benchmark
    def test_rule_builder_invalid_author_list_type(self):
        """Test RuleBuilder with invalid author list type returns None."""
        config = {"commit": {"ignore_authors": "not_a_list"}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="ignore_authors", regex="", error="", suggest=""
        )

        # This should return None for invalid type
        rule = builder._build_author_list_rule(catalog_entry, "ignore_authors")
        assert rule is None

    @pytest.mark.benchmark
    def test_rule_builder_length_rule_with_format(self):
        """Test RuleBuilder length rule with formatted error message (lines 154-160)."""
        config = {"commit": {"max_length": 50}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="max_length",
            regex="",
            error="Message too long: max {max_len} characters",
            suggest="Keep message short",
        )

        # This should create a rule with formatted error
        rule = builder._build_length_rule(catalog_entry, "max_length")
        assert rule is not None
        assert rule.check == "max_length"
        assert rule.error == "Message too long: max 50 characters"
        assert rule.suggest == "Keep message short"
        assert rule.value == 50

    @pytest.mark.benchmark
    def test_rule_builder_merge_base_rule_valid_target(self):
        """Test RuleBuilder merge base rule with valid target (line 193)."""
        config = {"branch": {"require_rebase_target": "main"}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="require_rebase_target",
            regex="",
            error="Branch must be rebased on target",
            suggest="Rebase on target branch",
        )

        # This should create a rule with regex target
        rule = builder._build_merge_base_rule(catalog_entry)
        assert rule is not None
        assert rule.check == "require_rebase_target"
        assert rule.regex == "main"
        assert rule.error == "Branch must be rebased on target"
        assert rule.suggest == "Rebase on target branch"

    @pytest.mark.benchmark
    def test_rule_builder_boolean_rule_enabled(self):
        """Test RuleBuilder boolean rule when enabled (line 236)."""
        config = {"commit": {"require_signed_off_by": True}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="require_signed_off_by",
            regex="^Signed-off-by:",
            error="Missing signoff",
            suggest="Add Signed-off-by line",
        )

        # This should create a rule when boolean is True
        rule = builder._build_boolean_rule(catalog_entry, builder.commit_config)
        assert rule is not None
        assert rule.check == "require_signed_off_by"
        assert rule.regex == "^Signed-off-by:"
        assert rule.error == "Missing signoff"
        assert rule.suggest == "Add Signed-off-by line"
        assert rule.value is True

    @pytest.mark.benchmark
    def test_rule_builder_boolean_rule_subject_disabled(self):
        """Test RuleBuilder boolean rule for subject checks when disabled (line 232)."""
        config = {"commit": {"subject_capitalized": False}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="subject_capitalized",
            regex="^[A-Z]",
            error="Subject must be capitalized",
            suggest="Capitalize first letter",
        )

        # This should return None when subject_capitalized is False (line 232)
        rule = builder._build_boolean_rule(catalog_entry, builder.commit_config)
        assert rule is None


# Additional coverage tests
class TestRuleBuilderAdditionalCoverage:
    """Additional tests for comprehensive rule_builder.py coverage."""

    def test_build_length_rule_with_non_integer(self):
        """Test length rule building with non-integer config value."""
        config = {"commit": {"subject_max_length": "not an int"}}
        builder = RuleBuilder(config)
        rules = builder.build_all_rules()

        length_rules = [r for r in rules if r.check == "subject_max_length"]
        assert len(length_rules) == 0

    def test_build_author_list_rule_with_non_list(self):
        """Test author list rule building with non-list config value."""
        config = {"commit": {"ignore_authors": "not a list"}}
        builder = RuleBuilder(config)
        rules = builder.build_all_rules()

        author_rules = [r for r in rules if r.check == "ignore_authors"]
        assert len(author_rules) == 0

    def test_build_merge_base_rule_with_non_string(self):
        """Test merge base rule building with non-string config value."""
        config = {"branch": {"require_rebase_target": 123}}
        builder = RuleBuilder(config)
        rules = builder.build_all_rules()

        merge_rules = [r for r in rules if r.check == "merge_base"]
        assert len(merge_rules) == 0

    def test_build_merge_base_rule_with_empty_string(self):
        """Test merge base rule building with empty string."""
        config = {"branch": {"require_rebase_target": ""}}
        builder = RuleBuilder(config)
        rules = builder.build_all_rules()

        merge_rules = [r for r in rules if r.check == "merge_base"]
        assert len(merge_rules) == 0

    def test_build_allow_merge_commits_enabled(self):
        """Test building allow_merge_commits rule when enabled (default)."""
        config = {"commit": {"allow_merge_commits": True}}
        builder = RuleBuilder(config)
        rules = builder.build_all_rules()

        merge_rules = [r for r in rules if r.check == "allow_merge_commits"]
        assert len(merge_rules) == 0

    def test_build_length_rule_with_format(self):
        """Test length rule with format placeholder."""
        config = {"commit": {"subject_max_length": 72}}
        builder = RuleBuilder(config)

        from commit_check.rules_catalog import COMMIT_RULES

        catalog_entry = next(
            (r for r in COMMIT_RULES if r.check == "subject_max_length"), None
        )

        if catalog_entry:
            rule = builder._build_length_rule(catalog_entry, "subject_max_length")
            assert rule is not None
            assert "72" in rule.error

    def test_build_author_list_rule_with_empty_list(self):
        """Test author list rule building with empty list."""
        config = {"commit": {"ignore_authors": []}}
        builder = RuleBuilder(config)
        rules = builder.build_all_rules()

        author_rules = [r for r in rules if r.check == "ignore_authors"]
        assert len(author_rules) == 0


class TestValidationRuleToDict:
    """Test ValidationRule to_dict edge cases."""

    def test_to_dict_with_all_fields(self):
        """Test to_dict with all fields populated."""
        rule = ValidationRule(
            check="author_name",
            regex=r"^[A-Z].*",
            error="Invalid author",
            suggest="Use proper name",
            value=True,
            allowed=["Alice", "Bob"],
            ignored=["bot"],
        )

        result = rule.to_dict()

        assert result["check"] == "author_name"
        assert result["regex"] == r"^[A-Z].*"
        assert result["error"] == "Invalid author"
        assert result["suggest"] == "Use proper name"
        assert result["value"] is True
        assert result["allowed"] == ["Alice", "Bob"]
        assert result["allowed_types"] == ["Alice", "Bob"]
        assert result["ignored"] == ["bot"]

    def test_to_dict_with_minimal_fields(self):
        """Test to_dict with minimal fields."""
        rule = ValidationRule(check="message")

        result = rule.to_dict()

        assert result["check"] == "message"
        assert result["regex"] == ""
        assert result["error"] == ""
        assert result["suggest"] == ""
        assert "value" not in result
        assert "allowed" not in result
        assert "ignored" not in result
