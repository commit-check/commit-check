"""Tests for commit_check.api – the public Python API."""

import pytest
from unittest.mock import patch
from commit_check.api import (
    validate_message,
    validate_branch,
    validate_tag,
    validate_author,
    validate_all,
    validate_push,
)


class TestValidateMessage:
    """Tests for validate_message()."""

    @pytest.mark.benchmark
    def test_valid_conventional_commit_passes(self):
        """A well-formed conventional commit message returns status='pass'."""
        result = validate_message("feat: add streaming endpoint")
        assert result["status"] == "pass"
        assert isinstance(result["checks"], list)

    @pytest.mark.benchmark
    def test_invalid_commit_returns_fail(self):
        """A non-conventional commit message returns status='fail'."""
        with patch("commit_check.engine.get_commit_info", return_value="test-user"):
            result = validate_message("bad commit message without type")
        assert result["status"] == "fail"

    @pytest.mark.benchmark
    def test_failed_check_has_required_keys(self):
        """Each failed check dict exposes check/status/value/error/suggest."""
        with patch("commit_check.engine.get_commit_info", return_value="test-user"):
            result = validate_message("wrong format")
        failed = [c for c in result["checks"] if c["status"] == "fail"]
        assert len(failed) >= 1
        for check in failed:
            assert "check" in check
            assert "status" in check
            assert "value" in check
            assert "error" in check
            assert "suggest" in check

    @pytest.mark.benchmark
    def test_result_contains_check_names(self):
        """Result checks list always contains the expected check names."""
        result = validate_message("docs: update readme")
        check_names = {c["check"] for c in result["checks"]}
        # The 'message' check must always be present
        assert "message" in check_names

    @pytest.mark.benchmark
    def test_no_terminal_output_produced(self, capsys):
        """validate_message must not print anything to stdout or stderr."""
        with patch("commit_check.engine.get_commit_info", return_value="test-user"):
            validate_message("bad commit no type")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "Commit rejected" not in captured.err

    @pytest.mark.benchmark
    def test_custom_config_restricts_types(self):
        """Custom config limiting allowed types causes unknown types to fail."""
        cfg = {"commit": {"allow_commit_types": ["feat", "fix"]}}
        # 'docs' type should now be disallowed
        with patch("commit_check.engine.get_commit_info", return_value="test-user"):
            result = validate_message("docs: update readme", config=cfg)
        assert result["status"] == "fail"

    @pytest.mark.benchmark
    def test_custom_config_pass(self):
        """Custom config with explicit types still passes valid commits."""
        cfg = {"commit": {"allow_commit_types": ["feat", "fix", "docs"]}}
        result = validate_message("feat: new feature", config=cfg)
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_fix_commit_passes(self):
        """fix: type always passes with default config."""
        result = validate_message("fix: correct null pointer dereference")
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_commit_with_scope_passes(self):
        """Commit with optional scope passes."""
        result = validate_message("feat(api): add user endpoint")
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_breaking_change_notation_passes(self):
        """Commit with breaking-change '!' notation passes."""
        result = validate_message("feat!: remove legacy auth")
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_wip_commit_fails_by_default(self):
        """WIP commits fail when allow_wip_commits=false (default in cchk.toml)."""
        cfg = {"commit": {"allow_wip_commits": False}}
        with patch("commit_check.engine.get_commit_info", return_value="test-user"):
            result = validate_message("WIP: half-baked change", config=cfg)
        assert result["status"] == "fail"

    @pytest.mark.benchmark
    def test_empty_message_returns_fail(self):
        """Empty commit messages fail the message check."""
        cfg = {"commit": {"allow_empty_commits": False}}
        with patch("commit_check.engine.get_commit_info", return_value="test-user"):
            result = validate_message("", config=cfg)
        assert result["status"] == "fail"


class TestValidateBranch:
    """Tests for validate_branch()."""

    @pytest.mark.benchmark
    def test_valid_feature_branch_passes(self):
        """feature/<name> branch passes conventional branch check."""
        result = validate_branch("feature/add-json-output")
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_valid_fix_branch_passes(self):
        """fix/<name> branch passes."""
        result = validate_branch("fix/null-pointer")
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_main_branch_passes(self):
        """'main' is always allowed."""
        result = validate_branch("main")
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_invalid_branch_fails(self):
        """Branch name without a conventional prefix fails."""
        result = validate_branch("my_random_branch")
        assert result["status"] == "fail"

    @pytest.mark.benchmark
    def test_result_contains_branch_check(self):
        """Result always contains a 'branch' check entry."""
        result = validate_branch("feature/test")
        check_names = {c["check"] for c in result["checks"]}
        assert "branch" in check_names

    @pytest.mark.benchmark
    def test_no_terminal_output_produced(self, capsys):
        """validate_branch must not print anything."""
        validate_branch("bad_branch_name")
        captured = capsys.readouterr()
        assert captured.out == ""

    @pytest.mark.benchmark
    def test_custom_allowed_types(self):
        """Custom branch types are respected."""
        cfg = {"branch": {"allow_branch_types": ["topic"]}}
        result = validate_branch("topic/my-change", config=cfg)
        assert result["status"] == "pass"


class TestValidateAuthor:
    """Tests for validate_author()."""

    @pytest.mark.benchmark
    def test_valid_name_and_email_pass(self):
        """Valid name and email both pass."""
        result = validate_author(name="Ada Lovelace", email="ada@example.com")
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_invalid_email_fails(self):
        """Email without '@' fails the author_email check."""
        result = validate_author(email="not-an-email")
        assert result["status"] == "fail"
        failed = [c for c in result["checks"] if c["status"] == "fail"]
        assert any(c["check"] == "author_email" for c in failed)

    @pytest.mark.benchmark
    def test_valid_email_passes(self):
        """Valid email passes."""
        result = validate_author(email="dev@example.org")
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_no_terminal_output_produced(self, capsys):
        """validate_author must not print anything."""
        validate_author(email="bad-email")
        captured = capsys.readouterr()
        assert captured.out == ""

    @pytest.mark.benchmark
    def test_both_name_and_email_validated(self):
        """When both name and email are passed, both checks appear in output."""
        result = validate_author(name="Jane Doe", email="jane@example.com")
        check_names = {c["check"] for c in result["checks"]}
        assert "author_name" in check_names
        assert "author_email" in check_names


class TestValidateAll:
    """Tests for validate_all()."""

    @pytest.mark.benchmark
    def test_all_valid_returns_pass(self):
        """Valid message and branch return combined pass."""
        result = validate_all(
            message="feat: implement search",
            branch="feature/implement-search",
        )
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_invalid_message_causes_fail(self):
        """Invalid commit message causes overall fail."""
        with patch("commit_check.engine.get_commit_info", return_value="test-user"):
            result = validate_all(
                message="not a conventional commit",
                branch="feature/something",
            )
        assert result["status"] == "fail"

    @pytest.mark.benchmark
    def test_invalid_branch_causes_fail(self):
        """Invalid branch name causes overall fail."""
        result = validate_all(
            message="feat: good commit",
            branch="bad_branch",
        )
        assert result["status"] == "fail"

    @pytest.mark.benchmark
    def test_combined_checks_appear_in_result(self):
        """Result checks list merges message and branch check entries."""
        result = validate_all(
            message="fix: patch auth",
            branch="fix/patch-auth",
        )
        check_names = {c["check"] for c in result["checks"]}
        assert "message" in check_names
        assert "branch" in check_names

    @pytest.mark.benchmark
    def test_no_args_returns_pass(self):
        """Called with no args, validate_all returns pass with empty checks."""
        result = validate_all()
        assert result["status"] == "pass"
        assert result["checks"] == []

    @pytest.mark.benchmark
    def test_no_terminal_output(self, capsys):
        """validate_all must not write to stdout or stderr."""
        with patch("commit_check.engine.get_commit_info", return_value="test"):
            validate_all(message="bad message", branch="bad_branch")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "Commit rejected" not in captured.err

    @pytest.mark.benchmark
    def test_author_validation_included(self):
        """Author checks appear in combined result when requested."""
        result = validate_all(
            message="feat: add feature",
            author_name="Valid Name",
            author_email="valid@example.com",
        )
        check_names = {c["check"] for c in result["checks"]}
        assert "author_name" in check_names
        assert "author_email" in check_names


class TestValidatePush:
    """Tests for validate_push() – the programmatic push safety API."""

    ZERO_SHA = "0000000000000000000000000000000000000000"

    @pytest.mark.benchmark
    def test_new_branch_push_passes(self):
        """Push to a new (zero-SHA) remote ref returns status='pass'."""
        push_info = f"refs/heads/feature/x abc1 refs/heads/feature/x {self.ZERO_SHA}"
        result = validate_push(push_info)
        assert result["status"] == "pass"
        checks = result["checks"]
        assert any(c["check"] == "no_force_push" for c in checks)

    @pytest.mark.benchmark
    def test_fast_forward_push_passes(self):
        """A fast-forward push (ancestor check returns 0) passes."""
        push_info = "refs/heads/main abc123 refs/heads/main def456"
        with patch("commit_check.engine.git_merge_base", return_value=0):
            result = validate_push(push_info)
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_force_push_fails(self):
        """A force push (ancestor check returns 1) returns status='fail'."""
        push_info = "refs/heads/main abc1 refs/heads/main def2"
        with patch("commit_check.engine.git_merge_base", return_value=1):
            result = validate_push(push_info)
        assert result["status"] == "fail"
        failed = [c for c in result["checks"] if c["status"] == "fail"]
        assert len(failed) >= 1
        assert failed[0]["check"] == "no_force_push"
        assert "Force push" in failed[0]["error"]

    @pytest.mark.benchmark
    def test_none_push_refs_passes(self):
        """Calling with push_refs=None (no stdin) returns pass."""
        result = validate_push(None)
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_custom_config_is_merged(self):
        """Custom config overrides are applied."""
        push_info = f"refs/heads/main abc1 refs/heads/main {self.ZERO_SHA}"
        # Even with allow_force_push=True in user config, validate_push
        # always forces it to False so blocking is always active.
        result = validate_push(
            push_info,
            config={"push": {"allow_force_push": True}},
        )
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_result_has_expected_structure(self):
        """Result dict has 'status' and 'checks' with correct keys."""
        push_info = f"refs/heads/main abc1 refs/heads/main {self.ZERO_SHA}"
        result = validate_push(push_info)
        assert "status" in result
        assert "checks" in result
        for c in result["checks"]:
            assert "check" in c
            assert "status" in c
            assert "value" in c
            assert "error" in c
            assert "suggest" in c


class TestSkippedStatus:
    """A skipped rule must not be reported as a passing one.

    An ignored author bypasses the policy entirely. Reporting that as
    ``pass`` made a run that validated nothing indistinguishable from one
    that validated everything, so consumers (the GitHub Action's summary,
    an agent reading the JSON) announced success for unchecked commits.
    """

    IGNORED = {"commit": {"ignore_authors": ["dependabot[bot]"]}}

    @pytest.mark.benchmark
    def test_ignored_author_reports_skip_not_pass(self):
        """Every rule reports 'skip', and the overall status follows."""
        with (
            patch(
                "commit_check.engine.get_git_config_value",
                return_value="dependabot[bot]",
            ),
            patch(
                "commit_check.engine.get_commit_info", return_value="dependabot[bot]"
            ),
        ):
            result = validate_message(
                "chore(deps): bump commit-check", config=self.IGNORED
            )

        assert result["status"] == "skip"
        assert result["checks"], "expected the rules to be reported, not dropped"
        assert {c["status"] for c in result["checks"]} == {"skip"}

    @pytest.mark.benchmark
    def test_skipped_checks_carry_no_value(self):
        """A skipped rule checked nothing, so it reports no checked value."""
        with (
            patch(
                "commit_check.engine.get_git_config_value",
                return_value="dependabot[bot]",
            ),
            patch(
                "commit_check.engine.get_commit_info", return_value="dependabot[bot]"
            ),
        ):
            result = validate_message(
                "chore(deps): bump commit-check", config=self.IGNORED
            )

        assert [c["value"] for c in result["checks"]] == [""] * len(result["checks"])

    @pytest.mark.benchmark
    def test_same_message_from_a_listed_author_still_passes(self):
        """The control: only the author differs, and the verdict is real.

        Without this the skip test would pass even if the rules had simply
        stopped running for everyone.
        """
        with (
            patch(
                "commit_check.engine.get_git_config_value", return_value="Ada Lovelace"
            ),
            patch("commit_check.engine.get_commit_info", return_value="Ada Lovelace"),
        ):
            result = validate_message(
                "chore(deps): bump commit-check", config=self.IGNORED
            )

        assert result["status"] == "pass"
        assert {c["status"] for c in result["checks"]} == {"pass"}
        assert any(c["value"] for c in result["checks"]), (
            "a real pass reports what it checked"
        )

    @pytest.mark.benchmark
    def test_a_failure_still_outranks_a_skip(self):
        """Overall status is 'skip' only when nothing ran at all."""
        with (
            patch(
                "commit_check.engine.get_git_config_value", return_value="Ada Lovelace"
            ),
            patch("commit_check.engine.get_commit_info", return_value="Ada Lovelace"),
        ):
            result = validate_message("wip nonsense", config=self.IGNORED)

        assert result["status"] == "fail"

    @pytest.mark.benchmark
    def test_combined_author_call_preserves_skip(self):
        """validate_author(name=..., email=...) merges two runs of checks.

        That merge had its own copy of the reduce-to-overall rule which
        defaulted to "pass", so a fully skipped combined call reported a
        pass even after the skip status existed.
        """
        cfg = {"commit": {"ignore_authors": ["dependabot[bot]"]}}
        with (
            patch(
                "commit_check.engine.get_git_config_value",
                return_value="dependabot[bot]",
            ),
            patch(
                "commit_check.engine.get_commit_info", return_value="dependabot[bot]"
            ),
        ):
            result = validate_author(
                name="whoever", email="who@example.com", config=cfg
            )

        assert result["status"] == "skip"
        assert {c["status"] for c in result["checks"]} == {"skip"}

    @pytest.mark.benchmark
    def test_validate_all_preserves_skip(self):
        """validate_all() merges every group and had the same private copy."""
        cfg = {
            "commit": {"ignore_authors": ["dependabot[bot]"]},
            "branch": {"ignore_authors": ["dependabot[bot]"]},
        }
        with (
            patch(
                "commit_check.engine.get_git_config_value",
                return_value="dependabot[bot]",
            ),
            patch(
                "commit_check.engine.get_commit_info", return_value="dependabot[bot]"
            ),
            patch("commit_check.engine.get_branch_name", return_value="main"),
        ):
            result = validate_all(
                message="chore(deps): bump commit-check",
                branch="dependabot/pip/commit-check-2.13.3",
                author_name="whoever",
                author_email="who@example.com",
                config=cfg,
            )

        assert result["status"] == "skip"
        assert {c["status"] for c in result["checks"]} == {"skip"}


class TestValidateTag:
    """Tests for validate_tag()."""

    @pytest.mark.benchmark
    def test_semver_tag_passes(self):
        result = validate_tag("v1.2.3")
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_bare_semver_tag_passes(self):
        result = validate_tag("1.2.3")
        assert result["status"] == "pass"

    @pytest.mark.benchmark
    def test_non_semver_tag_fails(self):
        result = validate_tag("release-candidate")
        assert result["status"] == "fail"
        failed = [c for c in result["checks"] if c["status"] == "fail"]
        assert failed[0]["rule_id"] == "CC401"

    @pytest.mark.benchmark
    def test_custom_pattern(self):
        cfg = {"tag": {"regex": r"^rel-\d+$"}}
        assert validate_tag("rel-7", config=cfg)["status"] == "pass"
        assert validate_tag("v1.2.3", config=cfg)["status"] == "fail"

    @pytest.mark.benchmark
    def test_multiline_tags(self):
        assert validate_tag("v1.0.0\nv1.0.1")["status"] == "pass"
        assert validate_tag("v1.0.0\nbad_tag")["status"] == "fail"

    @pytest.mark.benchmark
    def test_no_output(self, capfd):
        """validate_tag must not print anything."""
        validate_tag("bad_tag_name")
        out, err = capfd.readouterr()
        assert out == ""
        assert err == ""

    @pytest.mark.benchmark
    def test_empty_string_skips_instead_of_reading_git(self):
        """An explicit empty string names an empty tag list, not HEAD."""
        result = validate_tag("")
        assert result["status"] == "skip"
