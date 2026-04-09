"""Tests for commit_check.api – the public Python API."""

import pytest
from unittest.mock import patch
from commit_check.api import (
    validate_message,
    validate_branch,
    validate_author,
    validate_all,
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
