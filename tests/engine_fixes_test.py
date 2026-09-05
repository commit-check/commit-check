"""Validators name the correction when it is unambiguous, and only then."""

from unittest.mock import patch

from commit_check.engine import (
    ValidationContext,
    ValidationEngine,
    ValidationResult,
    count_warnings,
    overall_status,
)
from commit_check.rule_builder import RuleBuilder, ValidationRule

CONVENTIONAL = (
    r"^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\(.+\))?!?: \S.*"
)
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
    outcomes = ValidationEngine(rules).validate_all_detailed(
        ValidationContext(**context)
    )
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

    def test_a_fix_that_would_still_fail_is_withheld(self):
        """The helper and the validator agree today; the guard is for the day they drift."""
        rule = ValidationRule(
            check="subject_capitalized",
            error="Lowercase subject",
            suggest="Capitalise the subject",
        )
        with patch(
            "commit_check.engine.fix_subject_case", return_value="still lowercase"
        ):
            out = failed([rule], stdin_text="add x")
        assert out.fix == ""
        assert out.suggest == "Capitalise the subject"

    def test_plain_subject_is_capitalised_and_the_fix_passes_the_rule(self):
        rule = ValidationRule(
            check="subject_capitalized",
            error="Lowercase subject",
            suggest="Capitalise the subject",
        )
        out = failed([rule], stdin_text="add x")
        assert out.fix == "Add x"
        # The offered fix must itself satisfy the rule.
        engine = ValidationEngine([rule])
        assert (
            engine.validate_all_detailed(ValidationContext(stdin_text=out.fix))[
                0
            ].status
            == "pass"
        )


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

    @patch("commit_check.engine.get_commit_author_identity")
    @patch("commit_check.engine.get_git_user_identity")
    def test_trailer_uses_local_identity_for_pending_message(self, config, commit):
        config.return_value = ("Jane Doe", "jane@example.com")
        out = failed([self.rule()], stdin_text="feat: add x")
        assert out.fix == "feat: add x\n\nSigned-off-by: Jane Doe <jane@example.com>"
        assert out.suggest == (
            'Add the trailer "Signed-off-by: Jane Doe <jane@example.com>" '
            "(git commit --signoff, or --amend --signoff for an existing commit)"
        )
        # One git call is enough when the config is complete.
        config.assert_called_once()
        commit.assert_not_called()

    @patch("commit_check.engine.get_commit_author_identity")
    @patch("commit_check.engine.get_git_user_identity")
    def test_missing_config_part_falls_back_to_the_last_commit(self, config, commit):
        config.return_value = ("Jane Doe", "")
        commit.return_value = ("Old Name", "jane@example.com")
        out = failed([self.rule()], stdin_text="feat: add x")
        assert out.fix.endswith("Signed-off-by: Jane Doe <jane@example.com>")

    @patch("commit_check.engine.get_git_user_identity")
    @patch("commit_check.engine.get_commit_author_identity")
    @patch("commit_check.engine.get_commit_info")
    def test_trailer_uses_commit_author_for_a_revision(self, info, commit, config):
        info.side_effect = lambda fmt, rev=None: {"s": "feat: add x", "b": ""}.get(
            fmt, ""
        )
        commit.return_value = ("Rev Author", "rev@example.com")
        out = failed([self.rule()], rev="abc123")
        assert out.fix.endswith("Signed-off-by: Rev Author <rev@example.com>")
        commit.assert_called_once_with("abc123")
        config.assert_not_called()

    @patch("commit_check.engine.get_commit_author_identity", return_value=("", ""))
    @patch("commit_check.engine.get_git_user_identity", return_value=("", ""))
    def test_unknown_identity_keeps_generic_suggestion(self, _config, _commit):
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
        assert (
            out.suggest
            == 'Rename the branch to "feature/login" (git branch -m feature/login)'
        )

    def test_rename_command_quotes_shell_metacharacters(self):
        out = failed([self.rule()], stdin_text="Feature/$(whoami)")
        assert out.fix == "feature/$(whoami)"
        assert out.suggest.endswith("(git branch -m 'feature/$(whoami)')")

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
        rules = RuleBuilder(
            {"commit": {"allow_commit_types": ["feat", "fix"]}}
        ).build_all_rules()
        message_rules = [r for r in rules if r.check == "message"]
        # "docs" is not allowed here, so it is not a near-miss of anything.
        out = failed(message_rules, stdin_text="Docs: add x")
        assert out.fix == ""


class TestWarnSeverityInTheEngine:
    """A rule listed under ``warn`` is reported like a failure and counted like a pass."""

    def rules(self):
        return [
            ValidationRule(
                check="message", regex=CONVENTIONAL, error="e1", suggest="s1"
            ),
            ValidationRule(
                check="subject_imperative",
                error="Not imperative",
                suggest="Use the imperative",
                severity="warn",
            ),
        ]

    def test_detailed_outcome_is_warn_not_fail(self):
        outcomes = ValidationEngine(self.rules()).validate_all_detailed(
            ValidationContext(stdin_text="feat: added x")
        )
        by_check = {o.check: o for o in outcomes}
        assert by_check["message"].status == "pass"
        assert by_check["subject_imperative"].status == "warn"
        # The finding keeps its full detail; only the verdict changes.
        assert by_check["subject_imperative"].error == "Not imperative"
        assert by_check["subject_imperative"].suggest == "Use the imperative"
        assert overall_status(o.status for o in outcomes) == "pass"
        assert count_warnings(o.status for o in outcomes) == 1

    def test_a_real_failure_still_fails_alongside_a_warning(self):
        outcomes = ValidationEngine(self.rules()).validate_all_detailed(
            ValidationContext(stdin_text="added x")
        )
        assert {o.check: o.status for o in outcomes} == {
            "message": "fail",
            "subject_imperative": "warn",
        }
        assert overall_status(o.status for o in outcomes) == "fail"

    def test_text_mode_passes_and_names_the_warning_on_stderr(self, capsys):
        result = ValidationEngine(self.rules()).validate_all(
            ValidationContext(stdin_text="feat: added x", no_banner=True)
        )
        out, err = capsys.readouterr()
        assert result == ValidationResult.PASS
        assert "subject-imperative check warning ==> feat: added x" in out
        assert "does not fail the run" in out
        assert "Commit rejected" not in out
        assert "⚠ warnings (not enforced): subject-imperative" in err

    def test_text_mode_still_fails_on_an_enforced_rule(self, capsys):
        result = ValidationEngine(self.rules()).validate_all(
            ValidationContext(stdin_text="added x", no_banner=True)
        )
        out, _ = capsys.readouterr()
        assert result == ValidationResult.FAIL
        assert "message check failed ==> added x" in out
        assert "subject-imperative check warning ==> added x" in out

    def test_overall_status_only_counts_failures(self):
        assert overall_status(["warn", "pass"]) == "pass"
        assert overall_status(["warn", "skip"]) == "pass"
        assert overall_status(["warn", "fail"]) == "fail"
        assert overall_status(["skip", "skip"]) == "skip"
        assert count_warnings(["warn", "warn", "fail"]) == 2
