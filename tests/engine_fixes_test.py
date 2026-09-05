"""Validators name the correction when it is unambiguous, and only then."""

from unittest.mock import patch

from commit_check.engine import ValidationContext, ValidationEngine
from commit_check.rule_builder import RuleBuilder, ValidationRule

CONVENTIONAL = r"^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\(.+\))?!?: \S.*"
TYPES = [
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "revert",
    "style",
    "test",
]


def failed(rules, **context):
    outcomes = ValidationEngine(rules).validate_all_detailed(ValidationContext(**context))
    fails = [o for o in outcomes if o.status == "fail"]
    assert len(fails) == 1, outcomes
    return fails[0]


class TestMessageFixes:
    def rule(self):
        return ValidationRule(
            check="message",
            regex=CONVENTIONAL,
            error="Not conventional",
            suggest="Use a conventional type",
            allowed=TYPES,
        )

    def test_type_case_is_corrected(self):
        out = failed([self.rule()], stdin_text="Fix: add x")
        assert out.fix == "fix: add x"
        assert out.suggest == 'Use "fix: add x"'

    def test_misspelt_type_is_corrected(self):
        out = failed([self.rule()], stdin_text="feta(api): add x")
        assert out.fix == "feat(api): add x"

    def test_missing_colon_is_corrected(self):
        out = failed([self.rule()], stdin_text="docs update readme")
        assert out.fix == "docs: update readme"

    def test_body_is_kept_with_the_fix(self):
        out = failed([self.rule()], stdin_text="Fix: add x\n\nSome body")
        assert out.fix == "fix: add x\n\nSome body"
        assert out.suggest == 'Use "fix: add x"'

    def test_no_recognisable_type_keeps_generic_suggestion(self):
        out = failed([self.rule()], stdin_text="add x")
        assert out.fix == ""
        assert out.suggest == "Use a conventional type"

    def test_fix_field_is_serialised(self):
        out = failed([self.rule()], stdin_text="Fix: add x")
        assert out.to_dict()["fix"] == "fix: add x"

    def test_no_fix_serialises_as_empty_string(self):
        out = failed([self.rule()], stdin_text="add x")
        assert out.to_dict()["fix"] == ""


class TestSubjectCapitalizationFix:
    def test_description_is_capitalised(self):
        rule = ValidationRule(
            check="subject_capitalized",
            error="Lowercase subject",
            suggest="Capitalise the subject",
        )
        out = failed([rule], stdin_text="feat: add x")
        assert out.fix == "feat: Add x"
        assert out.suggest == 'Use "feat: Add x"'


class TestWipFix:
    def test_marker_is_dropped(self):
        rule = ValidationRule(
            check="allow_wip_commits",
            value=False,
            error="WIP commits are not allowed",
            suggest="Finish the work",
        )
        out = failed([rule], stdin_text="WIP: feat: add x\n\nbody")
        assert out.fix == "feat: add x\n\nbody"
        assert out.suggest == 'Drop the WIP marker: "feat: add x"'

    def test_bare_marker_keeps_generic_suggestion(self):
        rule = ValidationRule(
            check="allow_wip_commits",
            value=False,
            error="WIP commits are not allowed",
            suggest="Finish the work",
        )
        out = failed([rule], stdin_text="WIP")
        assert out.fix == ""
        assert out.suggest == "Finish the work"


class TestSignoffFix:
    def rule(self):
        return ValidationRule(
            check="require_signed_off_by",
            regex=r"Signed-off-by: .+ <.+@.+>",
            error="Missing sign-off",
            suggest="Run git commit --signoff",
        )

    @patch("commit_check.engine.get_commit_info", return_value="")
    @patch("commit_check.engine.get_git_config_value")
    def test_trailer_uses_local_identity_for_pending_message(self, config, _info):
        config.side_effect = {"user.name": "Jane Doe", "user.email": "jane@example.com"}.get
        out = failed([self.rule()], stdin_text="feat: add x")
        assert out.fix == "feat: add x\n\nSigned-off-by: Jane Doe <jane@example.com>"
        assert out.suggest == (
            'Add the trailer "Signed-off-by: Jane Doe <jane@example.com>" '
            "(git commit --signoff, or --amend --signoff for an existing commit)"
        )

    @patch("commit_check.engine.get_git_config_value", return_value="")
    @patch("commit_check.engine.get_commit_info")
    def test_trailer_uses_commit_author_for_a_revision(self, info, _config):
        info.side_effect = lambda fmt, rev=None: {
            "s": "feat: add x",
            "b": "",
            "an": "Rev Author",
            "ae": "rev@example.com",
        }.get(fmt, "")
        out = failed([self.rule()], rev="abc123")
        assert out.fix.endswith("Signed-off-by: Rev Author <rev@example.com>")

    @patch("commit_check.engine.get_commit_info", return_value="")
    @patch("commit_check.engine.get_git_config_value", return_value="")
    def test_unknown_identity_keeps_generic_suggestion(self, _config, _info):
        out = failed([self.rule()], stdin_text="feat: add x")
        assert out.fix == ""
        assert out.suggest == "Run git commit --signoff"


class TestBranchFix:
    def rule(self):
        return ValidationRule(
            check="branch",
            regex=r"^(feature|bugfix|hotfix)/.+|^main$",
            error="Bad branch name",
            suggest="Use type/description",
            allowed=["feature", "bugfix", "hotfix"],
        )

    def test_type_case_is_corrected(self):
        out = failed([self.rule()], stdin_text="Feature/login")
        assert out.fix == "feature/login"
        assert out.suggest == 'Rename the branch to "feature/login" (git branch -m feature/login)'

    def test_unrelated_prefix_keeps_generic_suggestion(self):
        out = failed([self.rule()], stdin_text="stuff/login")
        assert out.fix == ""
        assert out.suggest == "Use type/description"


class TestAiAttributionFix:
    def rule(self):
        return ValidationRule(
            check="ai_attribution",
            value="forbid",
            error="AI attribution forbidden",
            suggest="Remove AI trailers",
        )

    def test_trailer_lines_are_removed(self):
        message = (
            "feat: init\n\nSome body\n\n"
            "Co-authored-by: Claude <noreply@anthropic.com>\n"
            "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
        )
        out = failed([self.rule()], stdin_text=message)
        assert out.fix == "feat: init\n\nSome body"
        assert out.suggest.endswith("Remove the AI trailer lines and re-commit.")


class TestBuiltRulesCarryAllowedTypes:
    """The fix needs the allowed list, so the built-in rules must carry it."""

    def test_default_message_rule_names_the_fix(self):
        rules = RuleBuilder({"commit": {}}).build_all_rules()
        message_rules = [r for r in rules if r.check == "message"]
        out = failed(message_rules, stdin_text="Fix: add x")
        assert out.fix == "fix: add x"
        assert out.rule_id == "CC001"

    def test_custom_types_drive_the_fix(self):
        rules = RuleBuilder({"commit": {"allow_commit_types": ["feat", "fix"]}}).build_all_rules()
        message_rules = [r for r in rules if r.check == "message"]
        # "docs" is not allowed here, so it is not a near-miss of anything.
        out = failed(message_rules, stdin_text="Docs: add x")
        assert out.fix == ""
