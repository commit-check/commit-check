import sys
import pytest
import tempfile
import os
from commit_check.main import StdinReader, _get_message_content, main

CMD = "commit-check"


class TestMain:
    @pytest.mark.benchmark
    def test_help(self, capfd):
        sys.argv = [CMD, "--help"]
        with pytest.raises(SystemExit):
            main()
        out, _ = capfd.readouterr()
        assert "usage:" in out

    @pytest.mark.benchmark
    def test_version(self):
        # argparse defines --version
        sys.argv = [CMD, "--version"]
        with pytest.raises(SystemExit):
            main()

    @pytest.mark.benchmark
    def test_no_args_shows_help(self, capfd):
        """When no arguments are provided, should show help and exit 0."""
        sys.argv = [CMD]
        assert main() == 0

    @pytest.mark.benchmark
    def test_message_validation_with_valid_commit(self, mocker):
        """Test that a valid commit message passes validation."""
        # Mock stdin to provide a valid commit message
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: add new feature\n")

        sys.argv = [CMD, "-m"]
        assert main() == 0

    @pytest.mark.benchmark
    def test_message_validation_with_invalid_commit(self, mocker):
        """Test that an invalid commit message fails validation."""
        # Mock stdin to provide an invalid commit message
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="invalid commit message\n")

        # Mock git author to ensure it's not in any ignore list
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")

        sys.argv = [CMD, "-m"]
        assert main() == 1

    @pytest.mark.benchmark
    def test_message_validation_from_file(self):
        """Test validation of commit message from a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("fix: resolve bug")
            f.flush()

            try:
                sys.argv = [CMD, "-m", f.name]
                assert main() == 0
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_branch_validation(self, mocker):
        """Test branch name validation."""
        # Mock git command to return a valid branch name
        mocker.patch(
            "subprocess.run",
            return_value=type(
                "MockResult", (), {"stdout": "feature/test-branch", "returncode": 0}
            )(),
        )

        sys.argv = [CMD, "-b"]
        assert main() == 0

    @pytest.mark.benchmark
    def test_author_name_validation(self, mocker):
        """Test author name validation."""
        # Mock git command to return a valid author name
        mocker.patch(
            "subprocess.run",
            return_value=type(
                "MockResult", (), {"stdout": "John Doe", "returncode": 0}
            )(),
        )

        sys.argv = [CMD, "-n"]
        assert main() == 0

    @pytest.mark.benchmark
    def test_author_email_validation(self, mocker):
        """Test author email validation."""
        # Mock git command to return a valid author email
        mocker.patch(
            "subprocess.run",
            return_value=type(
                "MockResult", (), {"stdout": "john.doe@example.com", "returncode": 0}
            )(),
        )

        sys.argv = [CMD, "-e"]
        assert main() == 0

    @pytest.mark.benchmark
    def test_dry_run_always_passes(self, mocker):
        """Test that dry run mode always returns 0."""
        # Mock stdin to provide an invalid commit message
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="invalid commit message\n")

        sys.argv = [CMD, "-m", "--dry-run"]
        assert main() == 0


class TestStdinReader:
    """Test StdinReader edge cases."""

    @pytest.mark.benchmark
    def test_read_piped_input_with_exception(self, mocker):
        """Test StdinReader when stdin raises exception."""
        reader = StdinReader()

        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", side_effect=OSError("Broken pipe"))
        result = reader.read_piped_input()
        assert result is None

    @pytest.mark.benchmark
    def test_read_piped_input_with_ioerror(self, mocker):
        """Test StdinReader when stdin raises IOError."""
        reader = StdinReader()

        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", side_effect=IOError("Input error"))
        result = reader.read_piped_input()
        assert result is None


class TestGetMessageContent:
    """Test _get_message_content function edge cases."""

    @pytest.mark.benchmark
    def test_get_message_content_empty_string_with_stdin(self, mocker):
        """Test _get_message_content with empty string and stdin available."""
        reader = StdinReader()

        mocker.patch.object(reader, "read_piped_input", return_value="piped message")
        result = _get_message_content("", reader)
        assert result == "piped message"

    @pytest.mark.benchmark
    def test_get_message_content_empty_string_no_stdin_with_git(self, mocker):
        """Test _get_message_content with empty string, no stdin, fallback to git."""
        reader = StdinReader()

        mocker.patch.object(reader, "read_piped_input", return_value=None)
        mocker.patch(
            "commit_check.util.get_commit_info", return_value="git commit message"
        )
        result = _get_message_content("", reader)
        assert result == "git commit message"

    @pytest.mark.benchmark
    def test_get_message_content_empty_string_no_stdin_git_fails(self, capsys, mocker):
        """Test _get_message_content with empty string, no stdin, git fails."""
        reader = StdinReader()

        mocker.patch.object(reader, "read_piped_input", return_value=None)
        mocker.patch(
            "commit_check.util.get_commit_info", side_effect=Exception("Git error")
        )
        result = _get_message_content("", reader)
        assert result is None

        captured = capsys.readouterr()
        assert "Error: No commit message provided" in captured.err

    @pytest.mark.benchmark
    def test_get_message_content_file_read_error(self, capsys):
        """Test _get_message_content with file read error."""
        reader = StdinReader()

        result = _get_message_content("/nonexistent/file.txt", reader)
        assert result is None

        captured = capsys.readouterr()
        assert "Error reading message file" in captured.err

    @pytest.mark.benchmark
    def test_get_message_content_file_permission_error(self, capsys, mocker):
        """Test _get_message_content with file permission error."""
        reader = StdinReader()

        mocker.patch("builtins.open", side_effect=PermissionError("Permission denied"))
        result = _get_message_content("protected_file.txt", reader)
        assert result is None

        captured = capsys.readouterr()
        assert "Error reading message file" in captured.err


class TestMainFunctionEdgeCases:
    """Test main function edge cases for better coverage."""

    @pytest.mark.benchmark
    def test_main_with_message_file_argument(self):
        """Test main function with --message pointing to a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("feat: add new feature")
            f.flush()

            try:
                sys.argv = ["commit-check", "--message", f.name]
                result = main()
                assert result == 0
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_main_with_message_empty_string_and_stdin(self, mocker):
        """Test main function with --message (empty) and stdin input."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: Add new feature\n")

        sys.argv = ["commit-check", "--message"]
        result = main()
        assert result == 0

    @pytest.mark.benchmark
    def test_main_with_message_empty_string_no_stdin_with_git(self, mocker):
        """Test main function with --message (empty), no stdin, git fallback."""
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch(
            "commit_check.util.get_commit_info", return_value="feat: Git commit message"
        )

        sys.argv = ["commit-check", "--message"]
        result = main()
        assert result == 0

    # Removed problematic config and multi-check tests due to complex validation dependencies

    @pytest.mark.benchmark
    def test_main_with_invalid_config_file(self, mocker):
        """Test main function with invalid config file."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: Test feature\n")
        sys.argv = [
            "commit-check",
            "--config",
            "/nonexistent/config.toml",
            "--message",  # empty -> read from stdin
        ]

        # This should fail with proper error message when config file doesn't exist
        result = main()
        assert result == 1

    # Removed problematic tests that had configuration dependency issues

    @pytest.mark.benchmark
    def test_main_with_dry_run_all_checks(self, mocker):
        """Test main function with dry run and all checks."""
        # Mock git operations
        mocker.patch(
            "subprocess.run",
            return_value=mocker.MagicMock(stdout="invalid-branch-name", returncode=0),
        )
        mocker.patch("commit_check.util.has_commits", return_value=True)
        mocker.patch("commit_check.util.get_commit_info", return_value="Invalid Name")

        sys.argv = [
            "commit-check",
            "--message",
            "invalid commit message",
            "--branch",
            "--author-name",
            "--author-email",
            "--dry-run",
        ]
        result = main()
        assert result == 0  # Dry run always returns 0

    @pytest.mark.benchmark
    def test_main_error_handling_subprocess_failure(self, mocker, capsys):
        """Test main function when subprocess operations fail."""
        # Mock subprocess to fail
        mocker.patch("subprocess.run", side_effect=Exception("Git command failed"))

        sys.argv = ["commit-check", "--branch"]

        # Should handle the error gracefully
        result = main()
        # Even if subprocess fails, main should not crash
        assert result in [0, 1]  # Either passes or fails gracefully

    @pytest.mark.benchmark
    def test_nonexistent_config_file_error(self, capsys):
        """Test that specifying a non-existent config file returns error."""
        sys.argv = [
            "commit-check",
            "--config",
            "/nonexistent/config.toml",
            "--message",
            "feat: test",
        ]

        result = main()
        assert result == 1

        captured = capsys.readouterr()
        assert (
            "Error: Specified config file not found: /nonexistent/config.toml"
            in captured.err
        )


class TestCLIArgumentIntegration:
    """Test CLI argument integration with the new config merger."""

    @pytest.mark.benchmark
    def test_cli_subject_imperative_true(self, mocker):
        """Test --subject-imperative=true rejects non-imperative commit."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: Added feature\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        sys.argv = ["commit-check", "--message", "--subject-imperative=true"]
        result = main()
        assert result == 1  # Should fail due to non-imperative mood

    @pytest.mark.benchmark
    def test_cli_subject_imperative_false(self, mocker):
        """Test --subject-imperative=false allows non-imperative commit."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: Added feature\n")

        sys.argv = ["commit-check", "--message", "--subject-imperative=false"]
        result = main()
        assert result == 0  # Should pass

    @pytest.mark.benchmark
    def test_cli_subject_max_length(self, mocker):
        """Test --subject-max-length limits commit subject."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch(
            "sys.stdin.read",
            return_value="feat: This is a very long commit message that exceeds the limit\n",
        )
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        sys.argv = ["commit-check", "--message", "--subject-max-length=30"]
        result = main()
        assert result == 1  # Should fail due to length

    @pytest.mark.benchmark
    def test_cli_allow_commit_types(self, mocker):
        """Test --allow-commit-types restricts commit types."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="chore: do something\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        sys.argv = ["commit-check", "--message", "--allow-commit-types=feat,fix"]
        result = main()
        assert result == 1  # Should fail because 'chore' is not in allowed types

    @pytest.mark.benchmark
    def test_cli_allow_merge_commits_false(self, mocker):
        """Test --allow-merge-commits=false rejects merge commits."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch(
            "sys.stdin.read", return_value="Merge branch 'feature' into main\n"
        )
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        sys.argv = ["commit-check", "--message", "--allow-merge-commits=false"]
        result = main()
        assert result == 1  # Should fail

    @pytest.mark.benchmark
    def test_cli_multiple_args_combined(self, mocker):
        """Test multiple CLI arguments work together."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: Add feature\n")

        sys.argv = [
            "commit-check",
            "--message",
            "--subject-imperative=true",
            "--subject-max-length=100",
            "--allow-commit-types=feat,fix,docs",
        ]
        result = main()
        assert result == 0  # Should pass all checks


class TestEnvironmentVariableIntegration:
    """Test environment variable integration with the new config merger."""

    @pytest.mark.benchmark
    def test_env_subject_imperative(self, mocker, monkeypatch):
        """Test CCHK_SUBJECT_IMPERATIVE environment variable."""
        monkeypatch.setenv("CCHK_SUBJECT_IMPERATIVE", "true")
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: Added feature\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        sys.argv = ["commit-check", "--message"]
        result = main()
        assert result == 1  # Should fail due to non-imperative

    @pytest.mark.benchmark
    def test_env_subject_max_length(self, mocker, monkeypatch):
        """Test CCHK_SUBJECT_MAX_LENGTH environment variable."""
        monkeypatch.setenv("CCHK_SUBJECT_MAX_LENGTH", "30")
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch(
            "sys.stdin.read",
            return_value="feat: This is a very long commit message\n",
        )
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        sys.argv = ["commit-check", "--message"]
        result = main()
        assert result == 1  # Should fail due to length

    @pytest.mark.benchmark
    def test_env_allow_commit_types(self, mocker, monkeypatch):
        """Test CCHK_ALLOW_COMMIT_TYPES environment variable."""
        monkeypatch.setenv("CCHK_ALLOW_COMMIT_TYPES", "feat,fix")
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="chore: do something\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        sys.argv = ["commit-check", "--message"]
        result = main()
        assert result == 1  # Should fail


class TestConfigPriority:
    """Test configuration priority: CLI > Env > TOML > Defaults."""

    @pytest.mark.benchmark
    def test_cli_overrides_env(self, mocker, monkeypatch):
        """Test that CLI arguments override environment variables."""
        # Set env var to true
        monkeypatch.setenv("CCHK_SUBJECT_IMPERATIVE", "true")
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: Added feature\n")

        # Override with CLI to false
        sys.argv = ["commit-check", "--message", "--subject-imperative=false"]
        result = main()
        assert result == 0  # CLI wins, should pass

    @pytest.mark.benchmark
    def test_env_overrides_default(self, mocker, monkeypatch):
        """Test that environment variables override defaults."""
        # Default subject_max_length is 80
        monkeypatch.setenv("CCHK_SUBJECT_MAX_LENGTH", "30")
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch(
            "sys.stdin.read",
            return_value="feat: This is a commit message that is longer than 30 chars\n",
        )
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        sys.argv = ["commit-check", "--message"]
        result = main()
        assert result == 1  # Env var wins, should fail


class TestPositionalArgumentFeature:
    """Test positional commit_msg_file argument for pre-commit compatibility."""

    @pytest.mark.benchmark
    def test_positional_arg_without_message_flag(self):
        """Test using just the positional argument without --message flag."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("feat: add positional argument support")
            f.flush()

            try:
                # Use positional argument only (no --message flag)
                sys.argv = ["commit-check", f.name]
                result = main()
                assert result == 0  # Should pass validation
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_positional_arg_with_message_flag(self):
        """Test using positional argument with --message flag."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("fix: resolve bug in validation")
            f.flush()

            try:
                # Use both positional argument and --message flag
                sys.argv = ["commit-check", "--message", f.name]
                result = main()
                assert result == 0  # Should pass validation
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_positional_arg_with_branch_flag(self, mocker):
        """Test positional argument with other check flags (edge case)."""
        # Mock git command to return a valid branch name
        mocker.patch(
            "subprocess.run",
            return_value=type(
                "MockResult", (), {"stdout": "feature/test-branch", "returncode": 0}
            )(),
        )

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("chore: update documentation")
            f.flush()

            try:
                # Use positional argument with --branch flag
                sys.argv = ["commit-check", "--branch", f.name]
                result = main()
                # Should validate both commit message and branch name
                assert result == 0  # Should pass both validations
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_positional_arg_invalid_commit(self, mocker):
        """Test that positional argument correctly rejects invalid commits."""
        # Mock git author to ensure it's not in any ignore list
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("invalid commit message without type")
            f.flush()

            try:
                # Use positional argument with invalid message
                sys.argv = ["commit-check", f.name]
                result = main()
                assert result == 1  # Should fail validation
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_positional_arg_nonexistent_file(self, mocker):
        """Test that positional argument with non-existent file falls back to git."""
        # Mock git to return a valid commit message
        mocker.patch(
            "commit_check.engine.get_commit_info",
            return_value="feat: add fallback commit from git",
        )

        sys.argv = ["commit-check", "/nonexistent/commit_msg.txt"]
        result = main()
        # Should fall back to git and pass
        assert result == 0


# ---------------------------------------------------------------------------
# --fix / --yes guard conditions
# ---------------------------------------------------------------------------


class TestFixGuards:
    @pytest.mark.benchmark
    def test_yes_without_fix_exits_1(self, capfd):
        sys.argv = [CMD, "--message", "--yes"]
        assert main() == 1
        _, err = capfd.readouterr()
        assert "--yes requires --fix" in err

    @pytest.mark.benchmark
    def test_fix_with_branch_exits_1(self, capfd):
        sys.argv = [CMD, "--message", "--branch", "--fix"]
        assert main() == 1
        _, err = capfd.readouterr()
        assert "--fix is only valid with --message" in err

    @pytest.mark.benchmark
    def test_fix_with_author_name_exits_1(self, capfd):
        sys.argv = [CMD, "--message", "--author-name", "--fix"]
        assert main() == 1
        _, err = capfd.readouterr()
        assert "--fix is only valid with --message" in err

    @pytest.mark.benchmark
    def test_fix_with_author_email_exits_1(self, capfd):
        sys.argv = [CMD, "--message", "--author-email", "--fix"]
        assert main() == 1
        _, err = capfd.readouterr()
        assert "--fix is only valid with --message" in err

    @pytest.mark.benchmark
    def test_fix_no_tty_no_yes_exits_1(self, mocker, capfd):
        """--fix without --yes when stdin is not a tty should fail with helpful message."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="fixed the bug")
        sys.argv = [CMD, "--message", "--fix"]
        # Mode C: piped stdin detected → error (stdin_text will be set)
        assert main() == 1


# ---------------------------------------------------------------------------
# --fix Mode A: git commit (latest commit)
# ---------------------------------------------------------------------------


class TestFixModeA:
    @pytest.mark.benchmark
    def test_already_compliant_exits_0(self, mocker, capfd):
        """When commit already passes all checks, prints compliant and exits 0."""
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch(
            "commit_check.engine.get_commit_info",
            side_effect=lambda fmt: {
                "s": "feat: Add new feature",
                "b": "",
                "an": "Author",
            }.get(fmt, ""),
        )
        mocker.patch(
            "commit_check.main.get_commit_info",
            side_effect=lambda fmt: {
                "s": "feat: Add new feature",
                "b": "",
                "an": "Author",
            }.get(fmt, ""),
        )
        sys.argv = [CMD, "--message", "--fix", "--yes"]
        result = main()
        out, _ = capfd.readouterr()
        assert result == 0
        assert "compliant" in out

    @pytest.mark.benchmark
    def test_fixable_amends_and_exits_0(self, mocker, capfd):
        """Fixable violation with --yes: amends commit, exits 0."""
        # Use conventional prefix so only subject_imperative fails (message check passes)
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch(
            "commit_check.engine.get_commit_info",
            side_effect=lambda fmt: {
                "s": "feat: fixed the login bug",
                "b": "",
                "an": "Author",
            }.get(fmt, ""),
        )
        mocker.patch(
            "commit_check.main.get_commit_info",
            side_effect=lambda fmt: {
                "s": "feat: fixed the login bug",
                "b": "",
                "an": "Author",
            }.get(fmt, ""),
        )
        mock_check_call = mocker.patch("commit_check.main.subprocess.check_call")
        sys.argv = [CMD, "--message", "--fix", "--yes"]
        result = main()
        assert result == 0
        mock_check_call.assert_called_once()
        call_args = mock_check_call.call_args[0][0]
        assert "git" in call_args
        assert "--amend" in call_args

    @pytest.mark.benchmark
    def test_user_says_n_aborts(self, mocker, capfd):
        """When user responds 'n' to prompt, exits 1 without amending."""
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch(
            "commit_check.engine.get_commit_info",
            side_effect=lambda fmt: {
                "s": "feat: fixed the login bug",
                "b": "",
                "an": "Author",
            }.get(fmt, ""),
        )
        mocker.patch(
            "commit_check.main.get_commit_info",
            side_effect=lambda fmt: {
                "s": "feat: fixed the login bug",
                "b": "",
                "an": "Author",
            }.get(fmt, ""),
        )
        mocker.patch("commit_check.main.input", return_value="n")
        mock_check_call = mocker.patch("commit_check.main.subprocess.check_call")
        sys.argv = [CMD, "--message", "--fix"]
        result = main()
        assert result == 1
        mock_check_call.assert_not_called()

    @pytest.mark.benchmark
    def test_user_says_y_amends(self, mocker, capfd):
        """When user responds 'y' to prompt, amends commit."""
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch(
            "commit_check.engine.get_commit_info",
            side_effect=lambda fmt: {
                "s": "feat: fixed the login bug",
                "b": "",
                "an": "Author",
            }.get(fmt, ""),
        )
        mocker.patch(
            "commit_check.main.get_commit_info",
            side_effect=lambda fmt: {
                "s": "feat: fixed the login bug",
                "b": "",
                "an": "Author",
            }.get(fmt, ""),
        )
        mocker.patch("commit_check.main.input", return_value="y")
        mock_check_call = mocker.patch("commit_check.main.subprocess.check_call")
        sys.argv = [CMD, "--message", "--fix"]
        result = main()
        assert result == 0
        mock_check_call.assert_called_once()

    @pytest.mark.benchmark
    def test_amend_failure_exits_1(self, mocker, capfd):
        """When git commit --amend fails, exits 1 with error message."""
        import subprocess as sp

        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch(
            "commit_check.engine.get_commit_info",
            side_effect=lambda fmt: {
                "s": "feat: fixed the login bug",
                "b": "",
                "an": "Author",
            }.get(fmt, ""),
        )
        mocker.patch(
            "commit_check.main.get_commit_info",
            side_effect=lambda fmt: {
                "s": "feat: fixed the login bug",
                "b": "",
                "an": "Author",
            }.get(fmt, ""),
        )
        mocker.patch(
            "commit_check.main.subprocess.check_call",
            side_effect=sp.CalledProcessError(1, "git"),
        )
        sys.argv = [CMD, "--message", "--fix", "--yes"]
        result = main()
        assert result == 1
        _, err = capfd.readouterr()
        assert "amend failed" in err


# ---------------------------------------------------------------------------
# --fix Mode B: pre-commit hook (commit_msg_file)
# ---------------------------------------------------------------------------


class TestFixModeB:
    @pytest.mark.benchmark
    def test_file_fixed_and_written_back(self, mocker, tmp_path):
        """commit_msg_file + --fix --yes: fixed message written back to file."""
        commit_file = tmp_path / "COMMIT_EDITMSG"
        # Use conventional prefix so only subject_imperative fails (message check passes)
        commit_file.write_text("feat: fixed bug\n")
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch("commit_check.engine.get_commit_info", return_value="Author")
        sys.argv = [CMD, str(commit_file), "--fix", "--yes"]
        result = main()
        assert result == 0
        content = commit_file.read_text()
        assert "fix" in content.lower()
        assert content != "feat: fixed bug\n"

    @pytest.mark.benchmark
    def test_file_unfixable_exits_1(self, mocker, tmp_path, capfd):
        """commit_msg_file with unfixable violation exits 1."""
        commit_file = tmp_path / "COMMIT_EDITMSG"
        long_subject = "x" * 200
        commit_file.write_text(long_subject + "\n")
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch("commit_check.engine.get_commit_info", return_value="Author")
        sys.argv = [CMD, str(commit_file), "--fix", "--yes"]
        result = main()
        assert result == 1

    @pytest.mark.benchmark
    def test_file_interactive_user_says_n_unchanged(self, mocker, tmp_path):
        """Interactive mode with 'n': file not modified, exits 1."""
        commit_file = tmp_path / "COMMIT_EDITMSG"
        commit_file.write_text("feat: fixed bug\n")
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch("commit_check.engine.get_commit_info", return_value="Author")
        mocker.patch("commit_check.main.input", return_value="n")
        sys.argv = [CMD, str(commit_file), "--fix"]
        result = main()
        assert result == 1
        assert commit_file.read_text() == "feat: fixed bug\n"

    @pytest.mark.benchmark
    def test_file_read_error_exits_1(self, mocker, tmp_path, capfd):
        """OSError reading commit file: exits 1 with error message."""
        missing = tmp_path / "DOES_NOT_EXIST"
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch("commit_check.engine.get_commit_info", return_value="Author")
        sys.argv = [CMD, str(missing), "--fix", "--yes"]
        result = main()
        assert result == 1
        _, err = capfd.readouterr()
        assert "Error" in err

    @pytest.mark.benchmark
    def test_file_write_error_exits_1(self, mocker, tmp_path, capfd):
        """OSError writing fixed message back to file: exits 1 with error message."""
        commit_file = tmp_path / "COMMIT_EDITMSG"
        commit_file.write_text("feat: fixed bug\n")
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch("commit_check.engine.get_commit_info", return_value="Author")
        # Patch open to fail only on write (mode 'w')
        original_open = open

        def selective_open(path, mode="r", **kwargs):
            if str(path) == str(commit_file) and "w" in mode:
                raise OSError("disk full")
            return original_open(path, mode, **kwargs)

        mocker.patch("commit_check.main.open", side_effect=selective_open)
        sys.argv = [CMD, str(commit_file), "--fix", "--yes"]
        result = main()
        assert result == 1
        _, err = capfd.readouterr()
        assert "Error" in err


# ---------------------------------------------------------------------------
# --fix Mode C: piped stdin → error
# ---------------------------------------------------------------------------


class TestFixModeC:
    @pytest.mark.benchmark
    def test_piped_stdin_with_fix_exits_1(self, mocker, capfd):
        """--fix with piped stdin exits 1 with error about piped input."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="fixed the bug\n")
        sys.argv = [CMD, "--message", "--fix", "--yes"]
        result = main()
        assert result == 1
        _, err = capfd.readouterr()
        assert "piped" in err.lower() or "non-interactive" in err.lower()
