"""Tests for commit_check.rule_builder module."""

from commit_check.rule_builder import ValidationRule, RuleBuilder
from commit_check.rules_catalog import RuleCatalogEntry
import pytest

# String constants used across tests
BAD_FORMAT_ERROR = "Bad format"


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

    @pytest.mark.benchmark
    def test_rule_builder_allow_branch_names_default(self):
        """Test RuleBuilder with default branch names (no allow_branch_names configured)."""
        config = {"branch": {"conventional_branch": True}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(check="branch", regex="", error="", suggest="")

        rule = builder._build_conventional_branch_rule(catalog_entry)
        assert rule is not None
        # Should include default branch names: master, main, HEAD, PR-*
        assert "(master)" in rule.regex
        assert "(main)" in rule.regex
        assert "(HEAD)" in rule.regex
        assert "(PR-.+)" in rule.regex

    @pytest.mark.benchmark
    def test_rule_builder_allow_branch_names_custom(self):
        """Test RuleBuilder with custom branch names (allow_branch_names configured)."""
        config = {
            "branch": {
                "conventional_branch": True,
                "allow_branch_names": ["develop", "staging", "production"],
            }
        }

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(check="branch", regex="", error="", suggest="")

        rule = builder._build_conventional_branch_rule(catalog_entry)
        assert rule is not None
        # Should include both default and custom branch names
        assert "(master)" in rule.regex
        assert "(main)" in rule.regex
        assert "(HEAD)" in rule.regex
        assert "(PR-.+)" in rule.regex
        assert "(develop)" in rule.regex
        assert "(staging)" in rule.regex
        assert "(production)" in rule.regex

    @pytest.mark.benchmark
    def test_rule_builder_allow_branch_names_empty_list(self):
        """Test RuleBuilder with empty allow_branch_names list."""
        config = {"branch": {"conventional_branch": True, "allow_branch_names": []}}

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(check="branch", regex="", error="", suggest="")

        rule = builder._build_conventional_branch_rule(catalog_entry)
        assert rule is not None
        # Should only include default branch names
        assert "(master)" in rule.regex
        assert "(main)" in rule.regex
        assert "(HEAD)" in rule.regex
        assert "(PR-.+)" in rule.regex

    @pytest.mark.benchmark
    def test_ai_agent_and_bot_branch_types_in_default(self):
        """AI agent and bot prefixes are valid by default."""
        import re
        from commit_check import DEFAULT_BRANCH_TYPES

        assert "ai" in DEFAULT_BRANCH_TYPES
        assert "claude" in DEFAULT_BRANCH_TYPES
        assert "codex" in DEFAULT_BRANCH_TYPES
        assert "copilot" in DEFAULT_BRANCH_TYPES
        assert "cursor" in DEFAULT_BRANCH_TYPES
        assert "dependabot" in DEFAULT_BRANCH_TYPES
        assert "renovate" in DEFAULT_BRANCH_TYPES

        config = {"branch": {"conventional_branch": True}}
        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(check="branch", regex="", error="", suggest="")
        rule = builder._build_conventional_branch_rule(catalog_entry)
        assert rule is not None

        valid_branches = [
            # AI agent branches
            "ai/refactor-auth-flow",
            "claude/stoic-hypatia-v65p1f",
            "claude/fix-login-bug",
            "codex/optimize-query",
            "copilot/add-login-page",
            "cursor/fix-header-bug",
            # Bot/automation branches
            "dependabot/go_modules/go-deps-c57c3fe1e0",
            "dependabot/npm_and_yarn/lodash-4.17.21",
            "dependabot/pip/certifi-2022.12.7",
            "renovate/lodash-5.x",
            "renovate/major-lodash-5.x",
        ]
        for branch in valid_branches:
            assert re.match(rule.regex, branch), f"Branch '{branch}' should be valid"

    @pytest.mark.benchmark
    def test_rule_builder_allow_branch_names_with_duplicates(self):
        """Test RuleBuilder with duplicate branch names in allow_branch_names."""
        config = {
            "branch": {
                "conventional_branch": True,
                "allow_branch_names": ["develop", "develop", "staging", "develop"],
            }
        }

        builder = RuleBuilder(config)
        allowed_names = builder._get_allowed_branch_names()
        # Should deduplicate while preserving order
        assert allowed_names == ["develop", "staging"]

    @pytest.mark.benchmark
    def test_message_pattern_takes_precedence(self):
        """When message_pattern is set, it replaces the auto-generated regex."""
        config = {
            "commit": {
                "conventional_commits": True,
                "message_pattern": r"^PROJ-\d+: .+",
            }
        }

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="message", regex="", error=BAD_FORMAT_ERROR, suggest="Use JIRA format"
        )

        rule = builder._build_conventional_commit_rule(catalog_entry)
        assert rule is not None
        assert rule.regex == r"^PROJ-\d+: .+"
        assert rule.error == BAD_FORMAT_ERROR
        assert "required pattern" in rule.suggest

    @pytest.mark.benchmark
    def test_message_pattern_overrides_conventional_commits(self):
        """message_pattern works even when conventional_commits is false."""
        config = {
            "commit": {
                "conventional_commits": False,
                "message_pattern": r"^\[ISSUE-\d+\] .+",
            }
        }

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="message",
            regex="",
            error=BAD_FORMAT_ERROR,
            suggest="Use correct format",
        )

        rule = builder._build_conventional_commit_rule(catalog_entry)
        assert rule is not None
        assert rule.regex == r"^\[ISSUE-\d+\] .+"

    @pytest.mark.benchmark
    def test_message_pattern_empty_falls_back(self):
        """When message_pattern is empty string, fall back to conventional commits."""
        config = {
            "commit": {
                "conventional_commits": True,
                "message_pattern": "",
                "allow_commit_types": ["feat", "fix"],
            }
        }

        builder = RuleBuilder(config)
        catalog_entry = RuleCatalogEntry(
            check="message", regex="", error=BAD_FORMAT_ERROR, suggest="..."
        )

        rule = builder._build_conventional_commit_rule(catalog_entry)
        assert rule is not None
        # Should use auto-generated regex, not empty string
        assert "feat" in rule.regex
        assert "fix" in rule.regex


class TestPushRuleBuilder:
    """Tests for push rule building."""

    @pytest.mark.benchmark
    def test_push_rule_not_built_when_force_push_allowed(self):
        """No rule is built when allow_force_push is True (default)."""
        config = {"push": {"allow_force_push": True}}
        builder = RuleBuilder(config)
        rules = builder.build_all_rules()
        push_rules = [r for r in rules if r.check == "no_force_push"]
        assert len(push_rules) == 0

    @pytest.mark.benchmark
    def test_push_rule_built_when_force_push_disabled(self):
        """A rule is built when allow_force_push is False."""
        config = {"push": {"allow_force_push": False}}
        builder = RuleBuilder(config)
        rules = builder.build_all_rules()
        push_rules = [r for r in rules if r.check == "no_force_push"]
        assert len(push_rules) == 1
        assert push_rules[0].error == "Force push is not allowed"
        assert push_rules[0].suggest is not None

    @pytest.mark.benchmark
    def test_push_rule_not_built_by_default(self):
        """No rule is built with empty config (default: allow force push)."""
        builder = RuleBuilder({})
        rules = builder.build_all_rules()
        push_rules = [r for r in rules if r.check == "no_force_push"]
        assert len(push_rules) == 0

    @pytest.mark.benchmark
    def test_push_rule_unknown_check_returns_none(self):
        """A push rule with an unrecognized check name returns None."""
        builder = RuleBuilder({})
        unknown_entry = RuleCatalogEntry(check="unknown_push_check")
        rule = builder._build_push_rule(unknown_entry)
        assert rule is None


class TestAiAttributionRuleBuilder:
    """Tests for AI attribution rule building."""

    @pytest.mark.benchmark
    def test_ai_attribution_ignore_returns_none(self):
        """ai_attribution='ignore' (default) returns None."""
        config = {"commit": {"ai_attribution": "ignore"}}
        builder = RuleBuilder(config)
        entry = RuleCatalogEntry(check="ai_attribution")
        rule = builder._build_ai_attribution_rule(entry)
        assert rule is None

    @pytest.mark.benchmark
    def test_ai_attribution_forbid_creates_rule(self):
        """ai_attribution='forbid' creates a validation rule."""
        config = {"commit": {"ai_attribution": "forbid"}}
        builder = RuleBuilder(config)
        entry = RuleCatalogEntry(check="ai_attribution")
        rule = builder._build_ai_attribution_rule(entry)
        assert rule is not None
        assert rule.check == "ai_attribution"
        assert rule.value == "forbid"
        assert rule.allowed == ["assisted-by"]  # default style

    @pytest.mark.benchmark
    def test_ai_attribution_require_creates_rule(self):
        """ai_attribution='require' creates a validation rule."""
        config = {"commit": {"ai_attribution": "require"}}
        builder = RuleBuilder(config)
        entry = RuleCatalogEntry(check="ai_attribution")
        rule = builder._build_ai_attribution_rule(entry)
        assert rule is not None
        assert rule.check == "ai_attribution"
        assert rule.value == "require"
        assert rule.allowed == ["assisted-by"]  # default

    @pytest.mark.benchmark
    def test_ai_attribution_with_custom_trailer_style(self):
        """Custom ai_trailer_style is reflected in the rule."""
        config = {
            "commit": {
                "ai_attribution": "require",
                "ai_trailer_style": "co-authored-by",
            }
        }
        builder = RuleBuilder(config)
        entry = RuleCatalogEntry(check="ai_attribution")
        rule = builder._build_ai_attribution_rule(entry)
        assert rule is not None
        assert rule.value == "require"
        assert rule.allowed == ["co-authored-by"]

    @pytest.mark.benchmark
    def test_ai_trailer_style_ignore_returns_none(self):
        """When ai_attribution='ignore', ai_trailer_style returns None."""
        config = {
            "commit": {"ai_attribution": "ignore", "ai_trailer_style": "assisted-by"}
        }
        builder = RuleBuilder(config)
        entry = RuleCatalogEntry(check="ai_trailer_style")
        rule = builder._build_ai_trailer_style_rule(entry)
        assert rule is None

    @pytest.mark.benchmark
    def test_ai_trailer_style_creates_rule(self):
        """ai_trailer_style creates a rule when ai_attribution is not ignore."""
        config = {
            "commit": {
                "ai_attribution": "forbid",
                "ai_trailer_style": "assisted-by",
            }
        }
        builder = RuleBuilder(config)
        entry = RuleCatalogEntry(check="ai_trailer_style")
        rule = builder._build_ai_trailer_style_rule(entry)
        assert rule is not None
        assert rule.check == "ai_trailer_style"
        assert rule.value == "assisted-by"

    @pytest.mark.benchmark
    def test_ai_trailer_style_co_author(self):
        """ai_trailer_style='co-authored-by' is passed through."""
        config = {
            "commit": {
                "ai_attribution": "require",
                "ai_trailer_style": "co-authored-by",
            }
        }
        builder = RuleBuilder(config)
        entry = RuleCatalogEntry(check="ai_trailer_style")
        rule = builder._build_ai_trailer_style_rule(entry)
        assert rule is not None
        assert rule.value == "co-authored-by"

    @pytest.mark.benchmark
    def test_build_all_rules_includes_ai(self):
        """build_all_rules includes AI attribution rules when configured."""
        config = {"commit": {"ai_attribution": "forbid"}}
        builder = RuleBuilder(config)
        rules = builder.build_all_rules()
        ai_rules = [
            r for r in rules if r.check in ("ai_attribution", "ai_trailer_style")
        ]
        assert len(ai_rules) >= 1
        assert any(r.check == "ai_attribution" for r in ai_rules)

    @pytest.mark.benchmark
    def test_build_all_rules_no_ai_by_default(self):
        """build_all_rules does not include AI rules by default."""
        builder = RuleBuilder({})
        rules = builder.build_all_rules()
        ai_rules = [
            r for r in rules if r.check in ("ai_attribution", "ai_trailer_style")
        ]
        assert len(ai_rules) == 0
