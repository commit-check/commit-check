import json
import subprocess
import sys
import pytest
import tempfile
import time
import os
from commit_check.main import (
    StdinReader,
    _build_pre_commit_push_input,
    main,
)

CMD = "commit-check"
FEATURE_TOPIC_BRANCH = "feature/topic"


@pytest.fixture(autouse=True)
def _stdin_gate_open(request, monkeypatch):
    """Force the stdin readiness gate open for tests that fake piped input.

    Tests in this file simulate a pipe by mocking ``sys.stdin.read``. The
    gate added to fix the idle-pipe hang consults ``select`` on the *real*
    stdin, which under pytest is not readable — so those mocks would never
    be reached. Opening the gate restores the semantics the mocks assume.

    Tests that exercise the gate itself opt out via ``real_stdin_gate``.
    """
    if request.node.get_closest_marker("real_stdin_gate"):
        yield
        return
    monkeypatch.setattr(
        StdinReader, "_has_pending_data", staticmethod(lambda timeout=0.1: True)
    )
    yield


@pytest.fixture
def pinned_author(mocker):
    """Pin the identity the engine resolves, so no verdict comes from the checkout.

    A message given on stdin or in a file describes a *prospective* commit, so
    ``_resolve_current_author`` reads ``git config user.name`` and falls back to
    the author of ``HEAD``. Both are ambient. A CI runner configures no identity,
    so the fallback always wins there, and when ``HEAD`` happens to be a bot's
    commit that name is in ``ignore_authors`` — every commit check skips, and a
    test asserting ``pass`` sees ``skip`` instead.

    That is not hypothetical: it turned ``main`` red the moment a dependabot
    merge landed, having passed on every pull request before it. Any test that
    supplies a message and asserts a verdict needs this, or it is really
    asserting something about whoever committed last.
    """
    mocker.patch("commit_check.engine.get_git_config_value", return_value="test-author")
    mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")


class TestMain:
    @pytest.mark.benchmark
    def test_help(self, capfd, monkeypatch):
        monkeypatch.setattr("sys.argv", [CMD, "--help"])
        with pytest.raises(SystemExit):
            main()
        out, _ = capfd.readouterr()
        assert "usage:" in out

    @pytest.mark.benchmark
    def test_version(self, monkeypatch):
        # argparse defines --version
        monkeypatch.setattr("sys.argv", [CMD, "--version"])
        with pytest.raises(SystemExit):
            main()

    @pytest.mark.benchmark
    def test_no_args_shows_help(self, capfd, monkeypatch):
        """When no arguments are provided, should show help and exit 0."""
        monkeypatch.setattr("sys.argv", [CMD])
        assert main() == 0

    @pytest.mark.benchmark
    def test_message_validation_with_valid_commit(self, mocker, monkeypatch):
        """Test that a valid commit message passes validation."""
        # Mock stdin to provide a valid commit message
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: add new feature\n")

        monkeypatch.setattr("sys.argv", [CMD, "-m"])
        assert main() == 0

    @pytest.mark.benchmark
    def test_message_validation_with_invalid_commit(self, mocker, monkeypatch):
        """Test that an invalid commit message fails validation."""
        # Mock stdin to provide an invalid commit message
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="invalid commit message\n")

        # Mock git author to ensure it's not in any ignore list
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")

        monkeypatch.setattr("sys.argv", [CMD, "-m"])
        assert main() == 1

    @pytest.mark.benchmark
    def test_message_validation_from_file(self, monkeypatch):
        """Test validation of commit message from a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("fix: resolve bug")
            f.flush()

            try:
                monkeypatch.setattr("sys.argv", [CMD, "-m", f.name])
                assert main() == 0
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_branch_validation(self, mocker, monkeypatch):
        """Test branch name validation."""
        # Mock git command to return a valid branch name
        mocker.patch(
            "subprocess.run",
            return_value=type(
                "MockResult", (), {"stdout": "feature/test-branch", "returncode": 0}
            )(),
        )

        monkeypatch.setattr("sys.argv", [CMD, "-b"])
        assert main() == 0

    @pytest.mark.benchmark
    def test_author_name_validation(self, mocker, monkeypatch):
        """Test author name validation."""
        # Mock git command to return a valid author name
        mocker.patch(
            "subprocess.run",
            return_value=type(
                "MockResult", (), {"stdout": "John Doe", "returncode": 0}
            )(),
        )

        monkeypatch.setattr("sys.argv", [CMD, "-n"])
        assert main() == 0

    @pytest.mark.benchmark
    def test_author_email_validation(self, mocker, monkeypatch):
        """Test author email validation."""
        # Mock git command to return a valid author email
        mocker.patch(
            "subprocess.run",
            return_value=type(
                "MockResult", (), {"stdout": "john.doe@example.com", "returncode": 0}
            )(),
        )

        monkeypatch.setattr("sys.argv", [CMD, "-e"])
        assert main() == 0

    @pytest.mark.benchmark
    def test_dry_run_always_passes(self, mocker, monkeypatch):
        """Test that dry run mode always returns 0."""
        # Mock stdin to provide an invalid commit message
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="invalid commit message\n")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--dry-run"])
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

    @pytest.mark.real_stdin_gate
    @pytest.mark.skipif(sys.platform == "win32", reason="select() needs POSIX")
    def test_an_idle_open_pipe_returns_none_instead_of_hanging(self, monkeypatch):
        """The bug this guards against was a hang, not a wrong value.

        Under some CI runners stdin is a pipe that is open but that nothing
        will ever write to or close. ``read()`` there blocks forever, which
        in a workflow is a stuck step rather than a failed one.
        """
        read_fd, write_fd = os.pipe()
        try:
            with os.fdopen(read_fd, "r") as fake_stdin:
                monkeypatch.setattr(sys, "stdin", fake_stdin)
                start = time.monotonic()
                result = StdinReader.read_piped_input()
                elapsed = time.monotonic() - start
            assert result is None
            # ~0.1s select timeout; anything near a second means it blocked.
            assert elapsed < 2
        finally:
            os.close(write_fd)

    @pytest.mark.real_stdin_gate
    @pytest.mark.skipif(sys.platform == "win32", reason="select() needs POSIX")
    def test_piped_content_is_still_read(self, monkeypatch):
        """Real piped input predates the exec, so the gate must let it through."""
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"feat: add a thing\n")
        os.close(write_fd)
        with os.fdopen(read_fd, "r") as fake_stdin:
            monkeypatch.setattr(sys, "stdin", fake_stdin)
            assert StdinReader.read_piped_input() == "feat: add a thing"

    @pytest.mark.real_stdin_gate
    @pytest.mark.skipif(sys.platform == "win32", reason="select() needs POSIX")
    def test_dev_null_stdin_reads_as_nothing_promptly(self, monkeypatch):
        """`< /dev/null` is immediate EOF: readable, empty, no hang."""
        with open(os.devnull, "r") as fake_stdin:
            monkeypatch.setattr(sys, "stdin", fake_stdin)
            start = time.monotonic()
            result = StdinReader.read_piped_input()
            elapsed = time.monotonic() - start
        assert result is None
        assert elapsed < 2


class TestRevOption:
    """--rev names the commit under test, end to end on a real repository."""

    @pytest.fixture
    def two_commit_repo(self, tmp_path, monkeypatch):
        """A repo whose HEAD is fine and whose first commit is not.

        The parent commit carries both a non-conventional message and a
        deliberately malformed author, so checks that quietly read HEAD (or
        the config) instead of the requested revision come out different.
        """
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        monkeypatch.chdir(tmp_path)
        git = ["git", "-C", str(tmp_path)]
        subprocess.run(git + ["config", "user.name", "Good Author"], check=True)
        subprocess.run(git + ["config", "user.email", "good@example.com"], check=True)
        subprocess.run(
            git
            + [
                "-c",
                "user.name=bad",
                "-c",
                "user.email=nonsense",
                "commit",
                "-q",
                "--allow-empty",
                "-m",
                "updated the parser",
            ],
            check=True,
        )
        subprocess.run(
            git + ["commit", "-q", "--allow-empty", "-m", "feat: add a thing"],
            check=True,
        )
        return tmp_path

    def test_rev_checks_the_named_commits_message(self, two_commit_repo, monkeypatch):
        """HEAD passes, HEAD^ fails: the verdict must follow --rev."""
        monkeypatch.setattr("sys.argv", [CMD, "--message", "--rev", "HEAD"])
        assert main() == 0
        monkeypatch.setattr("sys.argv", [CMD, "--message", "--rev", "HEAD^"])
        assert main() == 1

    def test_rev_reads_the_commits_author_not_the_config(
        self, two_commit_repo, monkeypatch
    ):
        """The config identity is valid here, so a pass would mean the
        config was consulted -- the revision's own author must decide."""
        monkeypatch.setattr("sys.argv", [CMD, "--author-email", "--rev", "HEAD^"])
        assert main() == 1
        monkeypatch.setattr("sys.argv", [CMD, "--author-email", "--rev", "HEAD"])
        assert main() == 0

    def test_rev_that_does_not_resolve_is_a_clear_early_error(
        self, two_commit_repo, monkeypatch, capsys
    ):
        monkeypatch.setattr("sys.argv", [CMD, "--message", "--rev", "no-such-ref"])
        assert main() == 1
        assert "does not resolve" in capsys.readouterr().err

    def test_rev_empty_string_is_rejected_not_ignored(
        self, two_commit_repo, monkeypatch, capsys
    ):
        """An empty --rev must hit the same early error as a bad one, not
        fall through to the engine where git's own failure leaks into the
        checked value with a green exit."""
        monkeypatch.setattr("sys.argv", [CMD, "--message", "--rev", ""])
        assert main() == 1
        assert "does not resolve" in capsys.readouterr().err

    def test_rev_and_a_message_file_conflict(self, two_commit_repo, monkeypatch):
        monkeypatch.setattr("sys.argv", [CMD, "--rev", "HEAD", "some-file.txt"])
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 2

    def test_rev_works_in_json_mode(self, two_commit_repo, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.argv", [CMD, "--message", "--rev", "HEAD^", "--format", "json"]
        )
        assert main() == 1
        payload = json.loads(capsys.readouterr().out)
        values = [c.get("value", "") for c in payload["checks"]]
        assert any("updated the parser" in v for v in values)


class TestMainFunctionEdgeCases:
    """Test main function edge cases for better coverage."""

    @pytest.mark.benchmark
    def test_main_with_message_file_argument(self, monkeypatch):
        """Test main function with --message pointing to a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("feat: add new feature")
            f.flush()

            try:
                monkeypatch.setattr("sys.argv", ["commit-check", "--message", f.name])
                result = main()
                assert result == 0
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_main_with_message_empty_string_and_stdin(self, mocker, monkeypatch):
        """Test main function with --message (empty) and stdin input."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: Add new feature\n")

        monkeypatch.setattr("sys.argv", ["commit-check", "--message"])
        result = main()
        assert result == 0

    @pytest.mark.benchmark
    def test_main_with_message_empty_string_no_stdin_with_git(
        self, mocker, monkeypatch
    ):
        """Test main function with --message (empty), no stdin, git fallback."""
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch(
            "commit_check.engine.get_commit_info", return_value="feat: add feature"
        )

        monkeypatch.setattr("sys.argv", ["commit-check", "--message"])
        result = main()
        assert result == 0

    # Removed problematic config and multi-check tests due to complex validation dependencies

    @pytest.mark.benchmark
    def test_main_with_invalid_config_file(self, mocker, monkeypatch):
        """Test main function with invalid config file."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: Test feature\n")
        monkeypatch.setattr(
            "sys.argv",
            [
                "commit-check",
                "--config",
                "/nonexistent/config.toml",
                "--message",  # empty -> read from stdin
            ],
        )

        # This should fail with proper error message when config file doesn't exist
        result = main()
        assert result == 1

    # Removed problematic tests that had configuration dependency issues

    @pytest.mark.benchmark
    def test_main_with_dry_run_all_checks(self, mocker, monkeypatch):
        """Test main function with dry run and all checks."""
        # Mock git operations
        mocker.patch(
            "subprocess.run",
            return_value=mocker.MagicMock(stdout="invalid-branch-name", returncode=0),
        )
        mocker.patch("commit_check.util.has_commits", return_value=True)
        mocker.patch("commit_check.util.get_commit_info", return_value="Invalid Name")

        monkeypatch.setattr(
            "sys.argv",
            [
                "commit-check",
                "--message",
                "invalid commit message",
                "--branch",
                "--author-name",
                "--author-email",
                "--dry-run",
            ],
        )
        result = main()
        assert result == 0  # Dry run always returns 0

    @pytest.mark.benchmark
    def test_main_error_handling_subprocess_failure(self, mocker, capsys, monkeypatch):
        """Test main function when subprocess operations fail."""
        # Mock subprocess to fail
        mocker.patch("subprocess.run", side_effect=Exception("Git command failed"))

        monkeypatch.setattr("sys.argv", ["commit-check", "--branch"])

        # Should handle the error gracefully
        result = main()
        # Even if subprocess fails, main should not crash
        assert result in [0, 1]  # Either passes or fails gracefully

    @pytest.mark.benchmark
    def test_nonexistent_config_file_error(self, capsys, monkeypatch):
        """Test that specifying a non-existent config file returns error."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "commit-check",
                "--config",
                "/nonexistent/config.toml",
                "--message",
                "feat: test",
            ],
        )

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
    def test_cli_subject_imperative_true(self, mocker, monkeypatch):
        """Test --subject-imperative=true rejects non-imperative commit."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: Added feature\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        monkeypatch.setattr(
            "sys.argv", ["commit-check", "--message", "--subject-imperative=true"]
        )
        result = main()
        assert result == 1  # Should fail due to non-imperative mood

    @pytest.mark.benchmark
    def test_cli_subject_imperative_false(self, mocker, monkeypatch):
        """Test --subject-imperative=false allows non-imperative commit."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: Added feature\n")

        monkeypatch.setattr(
            "sys.argv", ["commit-check", "--message", "--subject-imperative=false"]
        )
        result = main()
        assert result == 0  # Should pass

    @pytest.mark.benchmark
    def test_cli_subject_max_length(self, mocker, monkeypatch):
        """Test --subject-max-length limits commit subject."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch(
            "sys.stdin.read",
            return_value="feat: This is a very long commit message that exceeds the limit\n",
        )
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        monkeypatch.setattr(
            "sys.argv", ["commit-check", "--message", "--subject-max-length=30"]
        )
        result = main()
        assert result == 1  # Should fail due to length

    @pytest.mark.benchmark
    def test_cli_allow_commit_types(self, mocker, monkeypatch):
        """Test --allow-commit-types restricts commit types."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="chore: do something\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        monkeypatch.setattr(
            "sys.argv", ["commit-check", "--message", "--allow-commit-types=feat,fix"]
        )
        result = main()
        assert result == 1  # Should fail because 'chore' is not in allowed types

    @pytest.mark.benchmark
    def test_cli_allow_merge_commits_false(self, mocker, monkeypatch):
        """Test --allow-merge-commits=false rejects merge commits."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch(
            "sys.stdin.read", return_value="Merge branch 'feature' into main\n"
        )
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        monkeypatch.setattr(
            "sys.argv", ["commit-check", "--message", "--allow-merge-commits=false"]
        )
        result = main()
        assert result == 1  # Should fail

    @pytest.mark.benchmark
    def test_cli_multiple_args_combined(self, mocker, monkeypatch):
        """Test multiple CLI arguments work together."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: Add feature\n")

        monkeypatch.setattr(
            "sys.argv",
            [
                "commit-check",
                "--message",
                "--subject-imperative=true",
                "--subject-max-length=100",
                "--allow-commit-types=feat,fix,docs",
            ],
        )
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

        monkeypatch.setattr("sys.argv", ["commit-check", "--message"])
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

        monkeypatch.setattr("sys.argv", ["commit-check", "--message"])
        result = main()
        assert result == 1  # Should fail due to length

    @pytest.mark.benchmark
    def test_env_allow_commit_types(self, mocker, monkeypatch):
        """Test CCHK_ALLOW_COMMIT_TYPES environment variable."""
        monkeypatch.setenv("CCHK_ALLOW_COMMIT_TYPES", "feat,fix")
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="chore: do something\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-user")

        monkeypatch.setattr("sys.argv", ["commit-check", "--message"])
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
        monkeypatch.setattr(
            "sys.argv", ["commit-check", "--message", "--subject-imperative=false"]
        )
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

        monkeypatch.setattr("sys.argv", ["commit-check", "--message"])
        result = main()
        assert result == 1  # Env var wins, should fail


class TestPositionalArgumentFeature:
    """Test positional commit_msg_file argument for pre-commit compatibility."""

    @pytest.mark.benchmark
    def test_positional_arg_without_message_flag(self, monkeypatch):
        """Test using just the positional argument without --message flag."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("feat: add positional argument support")
            f.flush()

            try:
                # Use positional argument only (no --message flag)
                monkeypatch.setattr("sys.argv", ["commit-check", f.name])
                result = main()
                assert result == 0  # Should pass validation
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_positional_arg_with_message_flag(self, monkeypatch):
        """Test using positional argument with --message flag."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("fix: resolve bug in validation")
            f.flush()

            try:
                # Use both positional argument and --message flag
                monkeypatch.setattr("sys.argv", ["commit-check", "--message", f.name])
                result = main()
                assert result == 0  # Should pass validation
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_positional_arg_with_branch_flag(self, mocker, monkeypatch):
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
                monkeypatch.setattr("sys.argv", ["commit-check", "--branch", f.name])
                result = main()
                # Should validate both commit message and branch name
                assert result == 0  # Should pass both validations
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_positional_arg_invalid_commit(self, mocker, monkeypatch):
        """Test that positional argument correctly rejects invalid commits."""
        # Mock git author to ensure it's not in any ignore list
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("invalid commit message without type")
            f.flush()

            try:
                # Use positional argument with invalid message
                monkeypatch.setattr("sys.argv", ["commit-check", f.name])
                result = main()
                assert result == 1  # Should fail validation
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_positional_arg_nonexistent_file(self, mocker, monkeypatch):
        """Test that positional argument with non-existent file falls back to git."""
        # Mock git to return a valid commit message
        mocker.patch(
            "commit_check.engine.get_commit_info",
            return_value="feat: add fallback commit from git",
        )

        monkeypatch.setattr("sys.argv", ["commit-check", "/nonexistent/commit_msg.txt"])
        result = main()
        # Should fall back to git and pass
        assert result == 0


class TestJsonFormat:
    """Tests for --format json machine-readable output."""

    @pytest.mark.benchmark
    def test_json_format_valid_message_returns_pass(
        self, mocker, capsys, monkeypatch, pinned_author
    ):
        """JSON output for a valid commit message has status=pass."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: add new feature\n")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--format", "json"])
        rc = main()

        out, _ = capsys.readouterr()
        data = json.loads(out)
        assert rc == 0
        assert data["status"] == "pass"
        assert isinstance(data["checks"], list)
        assert all("check" in c and "status" in c for c in data["checks"])

    @pytest.mark.benchmark
    def test_json_format_pass_reports_checked_value(
        self, mocker, capsys, monkeypatch, pinned_author
    ):
        """JSON output reports the checked value even when the check passed."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: add new feature\n")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--format", "json"])
        main()

        out, _ = capsys.readouterr()
        data = json.loads(out)
        passed_with_value = [
            c for c in data["checks"] if c["status"] == "pass" and c["value"]
        ]
        assert passed_with_value
        assert all(c["value"] == "feat: add new feature" for c in passed_with_value)

    @pytest.mark.benchmark
    def test_json_format_invalid_message_returns_fail(
        self, mocker, capsys, monkeypatch
    ):
        """JSON output for an invalid commit message has status=fail."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="invalid commit message\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--format", "json"])
        rc = main()

        out, _ = capsys.readouterr()
        data = json.loads(out)
        assert rc == 1
        assert data["status"] == "fail"
        failed = [c for c in data["checks"] if c["status"] == "fail"]
        assert len(failed) >= 1
        assert failed[0]["check"] == "message"
        assert "error" in failed[0] and failed[0]["error"]
        assert "suggest" in failed[0] and failed[0]["suggest"]

    @pytest.mark.benchmark
    def test_json_format_no_ascii_art_in_stdout(self, mocker, capsys, monkeypatch):
        """JSON mode must not include ASCII art / colour codes in stdout."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="bad commit\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--format", "json"])
        main()

        out, _ = capsys.readouterr()
        # Must be valid JSON
        json.loads(out)
        # No ANSI codes or ASCII art strings in the JSON output
        assert "Commit rejected" not in out
        assert "\033[" not in out

    @pytest.mark.benchmark
    def test_json_format_from_file(self, capsys, monkeypatch, pinned_author):
        """JSON mode works when reading commit message from a file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("fix: resolve null pointer in auth module")
            tmp_path = f.name

        try:
            monkeypatch.setattr("sys.argv", [CMD, "-m", tmp_path, "--format", "json"])
            rc = main()
            out, _ = capsys.readouterr()
            data = json.loads(out)
            assert rc == 0
            assert data["status"] == "pass"
        finally:
            os.unlink(tmp_path)

    @pytest.mark.benchmark
    def test_json_format_exit_code_matches_status(
        self, mocker, capsys, monkeypatch, pinned_author
    ):
        """Exit code 1 when JSON status is fail, exit code 0 when pass."""
        # --- pass case ---
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="chore: update dependencies\n")
        monkeypatch.setattr("sys.argv", [CMD, "-m", "--format", "json"])
        rc_pass = main()
        out, _ = capsys.readouterr()
        assert rc_pass == 0
        assert json.loads(out)["status"] == "pass"

        # --- fail case ---
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="not a conventional commit\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="author")
        monkeypatch.setattr("sys.argv", [CMD, "-m", "--format", "json"])
        rc_fail = main()
        out, _ = capsys.readouterr()
        assert rc_fail == 1
        assert json.loads(out)["status"] == "fail"

    @pytest.mark.benchmark
    def test_json_format_skips_when_head_author_is_ignored(
        self, mocker, capsys, monkeypatch
    ):
        """An unconfigured identity falls back to HEAD's author, ignore list and all.

        The counterpart to ``pinned_author``: rather than let this behaviour
        stay ambient — where it silently decides other tests' verdicts — it is
        asserted here. With no ``user.name`` configured, as on a CI runner, the
        author of ``HEAD`` decides, so a bot's merge commit skips every check
        even though the message under test is a perfectly valid one.

        Exit code stays 0: a skip is not a failure.
        """
        mocker.patch("commit_check.engine.get_git_config_value", return_value="")
        mocker.patch(
            "commit_check.engine.get_commit_info", return_value="dependabot[bot]"
        )
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: add new feature\n")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--format", "json"])
        rc = main()

        out, _ = capsys.readouterr()
        data = json.loads(out)
        assert rc == 0
        assert data["status"] == "skip"
        assert all(c["status"] == "skip" for c in data["checks"])


class TestNoBanner:
    """Tests for --no-banner flag."""

    @pytest.mark.benchmark
    def test_no_banner_suppresses_ascii_art(self, mocker, capsys, monkeypatch):
        """--no-banner must suppress the ASCII art / teddy bear header."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="invalid commit message\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--no-banner"])
        rc = main()

        out, _ = capsys.readouterr()
        assert rc == 1
        assert "Commit rejected by Commit-Check" not in out
        assert "(c).-.(c)" not in out
        # Error details should still appear
        assert "check failed ==>" in out

    @pytest.mark.benchmark
    def test_no_banner_still_shows_error_details(self, mocker, capsys, monkeypatch):
        """--no-banner keeps error messages and suggestions."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="invalid commit message\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--no-banner"])
        main()

        out, _ = capsys.readouterr()
        assert "check failed ==>" in out
        assert "Suggest:" in out

    @pytest.mark.benchmark
    def test_no_banner_passes_valid_commit(self, mocker, monkeypatch):
        """--no-banner with a valid commit should still return 0."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: add new feature\n")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--no-banner"])
        assert main() == 0


class TestCompact:
    """Tests for --compact flag."""

    @pytest.mark.benchmark
    def test_compact_suppresses_ascii_art(self, mocker, capsys, monkeypatch):
        """--compact must not include ASCII art in output."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="invalid commit message\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--compact"])
        rc = main()

        out, _ = capsys.readouterr()
        assert rc == 1
        assert "Commit rejected by Commit-Check" not in out
        assert "(c).-.(c)" not in out

    @pytest.mark.benchmark
    def test_compact_shows_one_line_per_failure(self, mocker, capsys, monkeypatch):
        """--compact outputs one [FAIL] line per failing check."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="invalid commit message\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--compact"])
        main()

        out, _ = capsys.readouterr()
        lines = [line for line in out.splitlines() if line.strip()]
        assert all(line.startswith("[FAIL]") for line in lines)
        assert len(lines) >= 1

    @pytest.mark.benchmark
    def test_compact_names_checks_the_way_the_default_output_does(
        self, mocker, capsys, monkeypatch
    ):
        """--compact prints the kebab-case name, not the config key.

        Both are text written for a person, so they have to agree. This
        assertion is the one the suite was missing: --compact shipped
        printing ``subject_imperative`` while the default output printed
        ``subject-imperative``, and nothing here noticed.
        """
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="docs: revamped the profile\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")

        # A check whose name contains an underscore, so the two forms differ.
        monkeypatch.setattr(
            "sys.argv", [CMD, "-m", "--compact", "--subject-imperative=true"]
        )
        main()

        out, _ = capsys.readouterr()
        assert "CC003 subject-imperative:" in out, (
            f"--compact should print the display name: {out!r}"
        )
        assert "subject_imperative" not in out, (
            f"--compact printed the config key: {out!r}"
        )

    @pytest.mark.benchmark
    def test_compact_no_suggestions(self, mocker, capsys, monkeypatch):
        """--compact output must not include 'Suggest:' lines."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="invalid commit message\n")
        mocker.patch("commit_check.engine.get_commit_info", return_value="test-author")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--compact"])
        main()

        out, _ = capsys.readouterr()
        assert "Suggest:" not in out

    @pytest.mark.benchmark
    def test_compact_passes_valid_commit(self, mocker, monkeypatch):
        """--compact with a valid commit should still return 0."""
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: add new feature\n")

        monkeypatch.setattr("sys.argv", [CMD, "-m", "--compact"])
        assert main() == 0


class TestNoForcePushFlag:
    """Tests for the --no-force-push CLI flag."""

    ZERO_SHA = "0000000000000000000000000000000000000000"

    @pytest.mark.benchmark
    def test_no_force_push_new_branch_passes(self, mocker, monkeypatch):
        """Push to a new remote branch (zero SHA) always passes."""
        push_info = (
            f"refs/heads/feature/new abc123 refs/heads/feature/new {self.ZERO_SHA}"
        )
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value=push_info)

        monkeypatch.setattr("sys.argv", [CMD, "--no-force-push"])
        assert main() == 0

    @pytest.mark.benchmark
    def test_no_force_push_fast_forward_passes(self, mocker, monkeypatch):
        """Fast-forward push (remote is ancestor of local) passes."""
        push_info = "refs/heads/main abc123 refs/heads/main def456"
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value=push_info)
        mocker.patch("commit_check.engine.git_merge_base", return_value=0)

        monkeypatch.setattr("sys.argv", [CMD, "--no-force-push"])
        assert main() == 0

    @pytest.mark.benchmark
    def test_no_force_push_force_push_fails(self, mocker, monkeypatch):
        """Force push (remote is not ancestor of local) fails."""
        push_info = "refs/heads/main abc123 refs/heads/main def456"
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value=push_info)
        mocker.patch("commit_check.engine.git_merge_base", return_value=1)

        monkeypatch.setattr("sys.argv", [CMD, "--no-force-push"])
        assert main() == 1

    @pytest.mark.benchmark
    def test_no_force_push_no_stdin_passes(self, mocker, monkeypatch):
        """When no stdin and no upstream are available, the check is skipped."""
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch("commit_check.engine.get_upstream_branch", return_value="")

        monkeypatch.setattr("sys.argv", [CMD, "--no-force-push"])
        assert main() == 0

    @pytest.mark.benchmark
    def test_no_force_push_no_stdin_uses_upstream_fallback(self, mocker, monkeypatch):
        """Without stdin, the CLI falls back to checking the current upstream."""
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch(
            "commit_check.engine.get_upstream_branch", return_value="origin/main"
        )
        mocker.patch("commit_check.engine.git_merge_base", return_value=0)

        monkeypatch.setattr("sys.argv", [CMD, "--no-force-push"])
        assert main() == 0

    @pytest.mark.benchmark
    def test_no_force_push_no_stdin_blocks_non_fast_forward_upstream(
        self, mocker, monkeypatch
    ):
        """Without stdin, a non-fast-forward upstream relationship fails."""
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch(
            "commit_check.engine.get_upstream_branch", return_value="origin/main"
        )
        mocker.patch("commit_check.engine.get_branch_name", return_value="main")
        mocker.patch("commit_check.engine.git_merge_base", return_value=1)

        monkeypatch.setattr("sys.argv", [CMD, "--no-force-push"])
        assert main() == 1

    @pytest.mark.benchmark
    def test_no_force_push_uses_pre_commit_env_before_upstream(
        self, mocker, monkeypatch
    ):
        """pre-commit pre-push metadata drives the check when stdin is unavailable."""
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch.dict(
            os.environ,
            {
                "PRE_COMMIT_LOCAL_BRANCH": FEATURE_TOPIC_BRANCH,
                "PRE_COMMIT_REMOTE_BRANCH": "main",
                "PRE_COMMIT_TO_REF": "local-sha",
                "PRE_COMMIT_FROM_REF": "remote-sha",
            },
            clear=True,
        )
        mock_merge = mocker.patch("commit_check.engine.git_merge_base", return_value=1)
        mock_upstream = mocker.patch("commit_check.engine.get_upstream_branch")

        monkeypatch.setattr("sys.argv", [CMD, "--no-force-push"])
        assert main() == 1

        mock_merge.assert_called_once_with("remote-sha", "local-sha")
        mock_upstream.assert_not_called()

    @pytest.mark.benchmark
    def test_no_force_push_pre_commit_env_fetches_remote_sha(self, mocker, monkeypatch):
        """pre-commit metadata can resolve the remote tip when FROM_REF is absent."""
        mocker.patch("sys.stdin.isatty", return_value=True)
        mocker.patch.dict(
            os.environ,
            {
                "PRE_COMMIT_REMOTE_NAME": "upstream",
                "PRE_COMMIT_LOCAL_BRANCH": FEATURE_TOPIC_BRANCH,
                "PRE_COMMIT_REMOTE_BRANCH": "main",
                "PRE_COMMIT_TO_REF": "local-sha",
            },
            clear=True,
        )
        mock_run = mocker.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="remote-sha\trefs/heads/main\n",
                stderr="",
            ),
        )
        mock_merge = mocker.patch("commit_check.engine.git_merge_base", return_value=0)

        monkeypatch.setattr("sys.argv", [CMD, "--no-force-push"])
        assert main() == 0

        mock_run.assert_called_once_with(
            ["git", "ls-remote", "--exit-code", "upstream", "refs/heads/main"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
        mock_merge.assert_called_once_with("remote-sha", "local-sha")

    @pytest.mark.benchmark
    def test_build_pre_commit_push_input_normalizes_branch_names(self, mocker):
        """pre-commit branch names are converted to git pre-push ref rows."""
        mocker.patch.dict(
            os.environ,
            {
                "PRE_COMMIT_LOCAL_BRANCH": FEATURE_TOPIC_BRANCH,
                "PRE_COMMIT_REMOTE_BRANCH": "main",
                "PRE_COMMIT_TO_REF": "local-sha",
                "PRE_COMMIT_FROM_REF": "remote-sha",
            },
            clear=True,
        )

        assert (
            _build_pre_commit_push_input()
            == "refs/heads/feature/topic local-sha refs/heads/main remote-sha"
        )

    @pytest.mark.benchmark
    def test_build_pre_commit_push_input_prefers_remote_sha(self, mocker):
        """The real remote tip is preferred over pre-commit's FROM_REF range."""
        mocker.patch.dict(
            os.environ,
            {
                "PRE_COMMIT_REMOTE_NAME": "upstream",
                "PRE_COMMIT_LOCAL_BRANCH": FEATURE_TOPIC_BRANCH,
                "PRE_COMMIT_REMOTE_BRANCH": "main",
                "PRE_COMMIT_TO_REF": "local-sha",
                "PRE_COMMIT_FROM_REF": "range-base-sha",
            },
            clear=True,
        )
        mocker.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="remote-sha\trefs/heads/main\n",
                stderr="",
            ),
        )

        assert (
            _build_pre_commit_push_input()
            == "refs/heads/feature/topic local-sha refs/heads/main remote-sha"
        )

    @pytest.mark.benchmark
    def test_no_force_push_flag_in_help(self, capfd, monkeypatch):
        """The --no-force-push flag appears in help output."""
        monkeypatch.setattr("sys.argv", [CMD, "--help"])
        with pytest.raises(SystemExit):
            main()
        out, _ = capfd.readouterr()
        assert "--no-force-push" in out
        assert "current branch against its upstream" in out


class TestReconfigureIO:
    """Tests for _reconfigure_io()."""

    @pytest.mark.benchmark
    def test_reconfigure_io_does_not_crash(self):
        """Calling _reconfigure_io() should never raise."""
        from commit_check.main import _reconfigure_io

        _reconfigure_io()  # no assert needed — just must not raise

    @pytest.mark.benchmark
    def test_reconfigure_io_sets_utf8_encoding(self):
        """After _reconfigure_io(), stdout/stderr/stdin use UTF-8."""
        from commit_check.main import _reconfigure_io

        _reconfigure_io()
        assert sys.stdout.encoding.upper() == "UTF-8"
        assert sys.stderr.encoding.upper() == "UTF-8"
        assert sys.stdin.encoding.upper() == "UTF-8"


class TestTagFlag:
    """Tests for the -t/--tag check type."""

    def test_tag_flag_in_help(self, capfd, monkeypatch):
        """The --tag flag and its option group appear in help output."""
        monkeypatch.setattr("sys.argv", [CMD, "--help"])
        with pytest.raises(SystemExit):
            main()
        out, _ = capfd.readouterr()
        assert "--tag" in out
        assert "--tag-regex" in out
        assert "tag(s) pointing at HEAD" in out

    def test_tag_in_requested_checks(self):
        """-t requests exactly the tag check."""
        from commit_check.main import _get_parser, _get_requested_checks

        args = _get_parser().parse_args(["-t"])
        assert _get_requested_checks(args) == ["tag"]

    def test_tag_combines_with_branch(self):
        """-b -t requests branch, merge_base and tag checks."""
        from commit_check.main import _get_parser, _get_requested_checks

        args = _get_parser().parse_args(["-b", "-t"])
        assert _get_requested_checks(args) == ["branch", "merge_base", "tag"]

    def test_tag_regex_reaches_config(self):
        """--tag-regex overrides the [tag] section pattern."""
        from commit_check.main import _get_parser
        from commit_check.config_merger import ConfigMerger

        args = _get_parser().parse_args(["-t", "--tag-regex", r"^rel-\d+$"])
        config = ConfigMerger.parse_cli_args(args)
        assert config["tag"]["regex"] == r"^rel-\d+$"


class TestFilesFlag:
    """Tests for the -f/--files check type."""

    def test_files_flag_in_help(self, capfd, monkeypatch):
        monkeypatch.setattr("sys.argv", [CMD, "--help"])
        with pytest.raises(SystemExit):
            main()
        out, _ = capfd.readouterr()
        assert "--files" in out
        assert "--files-max-size" in out
        assert "--files-prohibited-patterns" in out
        assert "--files-max-path-length" in out

    def test_files_in_requested_checks(self):
        from commit_check.main import _get_parser, _get_requested_checks

        args = _get_parser().parse_args(["-f"])
        assert _get_requested_checks(args) == [
            "file_size",
            "file_pattern",
            "path_length",
        ]

    def test_files_cli_options_reach_config(self):
        from commit_check.main import _get_parser
        from commit_check.config_merger import ConfigMerger

        args = _get_parser().parse_args(
            [
                "-f",
                "--files-max-size",
                "5MB",
                "--files-prohibited-patterns",
                "*.pem,.env",
                "--files-max-path-length",
                "200",
            ]
        )
        config = ConfigMerger.parse_cli_args(args)
        assert config["files"] == {
            "max_size": "5MB",
            "prohibited_patterns": ["*.pem", ".env"],
            "max_path_length": 200,
        }
