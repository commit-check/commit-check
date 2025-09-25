"""Tests for commit_check.rule_builder module."""

from commit_check.rule_builder import ValidationRule, RuleBuilder
from commit_check.rules_catalog import RuleCatalogEntry


class TestValidationRule:
    def test_validation_rule_creation(self):
        """Test ValidationRule creation with all fields."""
        rule = ValidationRule(
            check="test_check",
            regex=r"^test:",
            error="Test error",
            suggest="Test suggestion",
            value=42,
            allowed=["allowed1", "allowed2"],
            ignored=["ignored1", "ignored2"],
        )

        assert rule.check == "test_check"
        assert rule.regex == r"^test:"
        assert rule.error == "Test error"
        assert rule.suggest == "Test suggestion"
        assert rule.value == 42
        assert rule.allowed == ["allowed1", "allowed2"]
        assert rule.ignored == ["ignored1", "ignored2"]

    def test_validation_rule_to_dict_with_allowed(self):
        """Test ValidationRule.to_dict with allowed field (line 34)."""
        rule = ValidationRule(
            check="allow_authors",
            regex="",
            error="Author not allowed",
            suggest="Use allowed author",
            allowed=["alice@example.com", "bob@example.com"],
        )

        result = rule.to_dict()
        expected = {
            "check": "allow_authors",
            "regex": "",
            "error": "Author not allowed",
            "suggest": "Use allowed author",
            "allowed": ["alice@example.com", "bob@example.com"],
            "allowed_types": [
                "alice@example.com",
                "bob@example.com",
            ],  # Backward compatibility
        }
        assert result == expected

    def test_validation_rule_to_dict_with_ignored(self):
        """Test ValidationRule.to_dict() method with ignored field."""
        rule = ValidationRule(check="test_check", ignored=["ignored1", "ignored2"])

        result = rule.to_dict()
        assert result["ignored"] == ["ignored1", "ignored2"]


class TestRuleBuilder:
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

    def test_rule_builder_conventional_branch_disabled(self):
        """Test RuleBuilder when conventional_branch is disabled (line 133)."""
        config = {"branch": {"conventional_branch": False}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(check="branch", regex="", error="", suggest="")

        # This should return None when conventional_branch is False
        rule = builder._build_conventional_branch_rule(catalog_entry)
        assert rule is None

    def test_rule_builder_allow_authors_list(self):
        """Test RuleBuilder with allow_authors list (line 176)."""
        config = {"commit": {"allow_authors": ["alice@example.com", "bob@example.com"]}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="allow_authors",
            regex="",
            error="Author not allowed",
            suggest="Use allowed author",
        )

        # This should create a rule with allowed authors
        rule = builder._build_author_list_rule(catalog_entry, "allow_authors")
        assert rule is not None
        assert rule.check == "allow_authors"
        assert rule.allowed == ["alice@example.com", "bob@example.com"]
        assert rule.error == "Author not allowed"
        assert rule.suggest == "Use allowed author"

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

    def test_rule_builder_empty_author_list(self):
        """Test RuleBuilder with empty author list returns None."""
        config = {"commit": {"allow_authors": []}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="allow_authors", regex="", error="", suggest=""
        )

        # This should return None for empty list
        rule = builder._build_author_list_rule(catalog_entry, "allow_authors")
        assert rule is None

    def test_rule_builder_missing_author_list(self):
        """Test RuleBuilder with missing author list returns None."""
        config = {"commit": {}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="allow_authors", regex="", error="", suggest=""
        )

        # This should return None for missing config
        rule = builder._build_author_list_rule(catalog_entry, "allow_authors")
        assert rule is None

    def test_rule_builder_invalid_author_list_type(self):
        """Test RuleBuilder with invalid author list type returns None."""
        config = {"commit": {"allow_authors": "not_a_list"}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="allow_authors", regex="", error="", suggest=""
        )

        # This should return None for invalid type
        rule = builder._build_author_list_rule(catalog_entry, "allow_authors")
        assert rule is None

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
