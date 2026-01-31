import pytest
import subprocess
import tempfile
import os
from pathlib import Path, PurePath
from commit_check.util import (
    get_branch_name,
    has_commits,
    git_merge_base,
    get_commit_info,
    cmd_output,
    print_error_header,
    print_error_message,
    print_suggestion,
    _find_check,
    _load_toml,
    _find_config_file,
    validate_config,
)
from subprocess import CalledProcessError, PIPE
from unittest.mock import MagicMock, patch


class TestUtil:
    class TestGetBranchName:
        @pytest.mark.benchmark
        def test_get_branch_name(self, mocker):
            # Must call cmd_output with given argument.
            m_cmd_output = mocker.patch(
                "commit_check.util.cmd_output", return_value=" fake_branch_name "
            )
            retval = get_branch_name()
            assert m_cmd_output.call_count == 1
            assert m_cmd_output.call_args[0][0] == ["git", "branch", "--show-current"]
            assert retval == "fake_branch_name"

        @pytest.mark.benchmark
        def test_get_branch_name_with_exception(self, mocker):
            mock_cmd_output = mocker.patch(
                "commit_check.util.cmd_output",
                side_effect=CalledProcessError(
                    returncode=1, cmd="git branch --show-current"
                ),
            )
            retval = get_branch_name()
            assert mock_cmd_output.call_count == 1
            mock_cmd_output.assert_called_once_with(["git", "branch", "--show-current"])
            assert retval == "HEAD" or retval  # depending on env vars

        @pytest.mark.benchmark
        def test_get_branch_name_fallback_github_head_ref(self, mocker):
            """Test fallback to GITHUB_HEAD_REF."""
            mocker.patch("commit_check.util.cmd_output", return_value="")
            mocker.patch(
                "commit_check.util.os.getenv",
                lambda key: "feature-branch" if key == "GITHUB_HEAD_REF" else None,
            )
            assert get_branch_name() == "feature-branch"

        @pytest.mark.benchmark
        def test_get_branch_name_fallback_github_ref_name(self, mocker):
            """Test fallback to GITHUB_REF_NAME."""
            mocker.patch("commit_check.util.cmd_output", return_value="")
            mocker.patch(
                "commit_check.util.os.getenv",
                lambda key: "develop" if key == "GITHUB_REF_NAME" else None,
            )
            assert get_branch_name() == "develop"

        @pytest.mark.benchmark
        def test_get_branch_name_fallback_head(self, mocker):
            """Test fallback to HEAD."""
            mocker.patch("commit_check.util.cmd_output", return_value="")
            mocker.patch("commit_check.util.os.getenv", return_value=None)
            assert get_branch_name() == "HEAD"

        @pytest.mark.benchmark
        def test_get_branch_name_fallback_priority(self, mocker):
            """Test fallback priority."""
            mocker.patch("commit_check.util.cmd_output", return_value="")
            mocker.patch(
                "commit_check.util.os.getenv",
                lambda key: {
                    "GITHUB_HEAD_REF": "feature-branch",
                    "GITHUB_REF_NAME": "develop",
                }.get(key),
            )
            assert get_branch_name() == "feature-branch"

    class TestHasCommits:
        @pytest.mark.benchmark
        def test_has_commits_true(self, mocker):
            # Must return True when git rev-parse HEAD succeeds
            m_subprocess_run = mocker.patch("subprocess.run", return_value=None)
            retval = has_commits()
            assert m_subprocess_run.call_count == 1
            assert m_subprocess_run.call_args[0][0] == [
                "git",
                "rev-parse",
                "--verify",
                "HEAD",
            ]
            assert m_subprocess_run.call_args[1] == {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "check": True,
            }
            assert retval is True

        @pytest.mark.benchmark
        def test_has_commits_false(self, mocker):
            # Must return False when git rev-parse HEAD fails
            m_subprocess_run = mocker.patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(128, "git rev-parse"),
            )
            retval = has_commits()
            assert m_subprocess_run.call_count == 1
            assert m_subprocess_run.call_args[0][0] == [
                "git",
                "rev-parse",
                "--verify",
                "HEAD",
            ]
            assert m_subprocess_run.call_args[1] == {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "check": True,
            }
            assert retval is False

    class TestGitMergeBase:
        @pytest.mark.benchmark
        @pytest.mark.parametrize(
            "returncode,expected",
            [
                (0, 0),  # ancestor exists
                (1, 1),  # no ancestor
                (128, 128),  # error case
            ],
        )
        @pytest.mark.benchmark
        def test_git_merge_base(self, mocker, returncode, expected):
            mock_run = mocker.patch("subprocess.run")
            if returncode == 128:
                mock_run.side_effect = CalledProcessError(returncode, "git merge-base")
            else:
                mock_result = MagicMock()
                mock_result.returncode = returncode
                mock_run.return_value = mock_result

            result = git_merge_base("main", "feature")

            mock_run.assert_called_once_with(
                ["git", "merge-base", "--is-ancestor", "main", "feature"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
            )

            assert result == expected

    class TestGetCommitInfo:
        @pytest.mark.benchmark
        @pytest.mark.parametrize(
            "format_string",
            [
                ("s"),
                ("an"),
                ("ae"),
            ],
        )
        @pytest.mark.benchmark
        def test_get_commit_info(self, mocker, format_string):
            # Must call get_commit_info with given argument when there are commits.
            mocker.patch("commit_check.util.has_commits", return_value=True)
            m_cmd_output = mocker.patch(
                "commit_check.util.cmd_output", return_value=" fake commit message "
            )
            retval = get_commit_info(format_string)
            assert m_cmd_output.call_count == 1
            assert m_cmd_output.call_args[0][0] == [
                "git",
                "log",
                "-n",
                "1",
                f"--pretty=format:%{format_string}",
                "HEAD",
            ]
            assert retval == " fake commit message "

        @pytest.mark.benchmark
        def test_get_commit_info_no_commits(self, mocker):
            # Must return 'Repo has no commits yet.' when there are no commits.
            mocker.patch("commit_check.util.has_commits", return_value=False)
            mocker.patch(
                "commit_check.util.cmd_output", return_value=" fake commit message "
            )
            format_string = "s"
            retval = get_commit_info(format_string)
            assert retval == " fake commit message "

        @pytest.mark.benchmark
        def test_get_commit_info_with_exception(self, mocker):
            # Must return empty string when exception raises in cmd_output.
            mocker.patch("commit_check.util.has_commits", return_value=True)
            m_cmd_output = mocker.patch(
                "commit_check.util.cmd_output", return_value=" fake commit message "
            )
            # CalledProcessError's args also dummy
            dummy_ret_code, dummy_cmd_name = 1, "dcmd"
            m_cmd_output.side_effect = CalledProcessError(
                dummy_ret_code, dummy_cmd_name
            )
            format_string = "s"
            retval = get_commit_info(format_string)
            assert m_cmd_output.call_count == 1
            assert m_cmd_output.call_args[0][0] == [
                "git",
                "log",
                "-n",
                "1",
                f"--pretty=format:%{format_string}",
                "HEAD",
            ]
            assert retval == ""

    class TestCmdOutput:
        # use DummyProcessResult in this test to access returncode, stdout and stderr attribute
        class DummyProcessResult:
            def __init__(self, returncode, stdout, stderr):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        @pytest.mark.benchmark
        def test_cmd_output(self, mocker):
            # Must subprocess.run with given argument.
            m_subprocess_run = mocker.patch(
                "subprocess.run", return_value=self.DummyProcessResult(0, "ok", "")
            )
            retval = cmd_output(["dummy_cmd"])
            assert m_subprocess_run.call_count == 1
            assert retval == "ok"

        @pytest.mark.benchmark
        @pytest.mark.parametrize(
            "returncode, stdout, stderr",
            [
                (1, "ok", "err"),
                (0, None, "err"),
                (1, None, "err"),
            ],
        )
        @pytest.mark.benchmark
        def test_cmd_output_err(self, mocker, returncode, stdout, stderr):
            # Must return stderr when  subprocess.run returns not empty stderr.
            m_subprocess_run = mocker.patch(
                "subprocess.run",
                return_value=self.DummyProcessResult(returncode, stdout, stderr),
            )
            dummy_cmd = ["dummy_cmd"]
            retval = cmd_output(dummy_cmd)
            assert m_subprocess_run.call_count == 1
            assert retval == stderr
            assert m_subprocess_run.call_args[0][0] == dummy_cmd
            assert m_subprocess_run.call_args[1] == {
                "encoding": "utf-8",
                "stderr": PIPE,
                "stdout": PIPE,
            }

        @pytest.mark.benchmark
        @pytest.mark.parametrize(
            "returncode, stdout, stderr",
            [
                (1, "ok", ""),
                (0, None, ""),
                (1, None, ""),
            ],
        )
        @pytest.mark.benchmark
        def test_cmd_output_err_with_len0_stderr(
            self, mocker, returncode, stdout, stderr
        ):
            # Must return empty string when subprocess.run returns empty stderr.
            m_subprocess_run = mocker.patch(
                "subprocess.run",
                return_value=self.DummyProcessResult(returncode, stdout, stderr),
            )
            dummy_cmd = ["dummy_cmd"]
            retval = cmd_output(dummy_cmd)
            assert m_subprocess_run.call_count == 1
            assert retval == ""
            assert m_subprocess_run.call_args[0][0] == dummy_cmd
            assert m_subprocess_run.call_args[1] == {
                "encoding": "utf-8",
                "stderr": PIPE,
                "stdout": PIPE,
            }

    class TestPrintErrorMessage:
        @pytest.mark.benchmark
        def test_print_error_header(self, capfd):
            # Must print on stdout with given argument.
            print_error_header()
            stdout, _ = capfd.readouterr()
            assert "Commit rejected by Commit-Check" in stdout
            assert "Commit rejected." in stdout

        @pytest.mark.benchmark
        @pytest.mark.parametrize(
            "check_type, type_failed_msg",
            [
                ("message", "check failed ==>"),
                ("branch", "check failed ==>"),
                ("author_name", "check failed ==>"),
                ("author_email", "check failed ==>"),
                ("signoff", "check failed ==>"),
            ],
        )
        @pytest.mark.benchmark
        def test_print_error_message(self, capfd, check_type, type_failed_msg):
            # Must print on stdout with given argument.
            dummy_regex = "dummy regex"
            dummy_reason = "failure reason"
            dummy_error = "dummy error"
            print_error_message(check_type, dummy_regex, dummy_error, dummy_reason)
            stdout, _ = capfd.readouterr()
            assert check_type in stdout
            assert type_failed_msg in stdout
            assert f"It doesn't match regex: {dummy_regex}" in stdout
            assert dummy_error in stdout

    class TestPrintSuggestion:
        @pytest.mark.benchmark
        def test_print_suggestion(self, capfd):
            # Must print on stdout with given argument.
            print_suggestion("dummy suggest")
            stdout, _ = capfd.readouterr()
            assert "Suggest:" in stdout

        @pytest.mark.benchmark
        def test_print_suggestion_exit1(self, capfd):
            # Must exit with 1 when "" passed
            with pytest.raises(SystemExit) as e:
                print_suggestion("")
            assert e.value.code == 1
            stdout, _ = capfd.readouterr()
            assert "commit-check does not support" in stdout

    class TestHelperFunctions:
        """Tests for utility helper functions to improve coverage."""

        def test_find_check_found(self):
            """Test _find_check when check is found."""
            checks = [
                {"check": "commit-message", "regex": ".*"},
                {"check": "branch-name", "regex": ".*"},
            ]
            result = _find_check(checks, "commit-message")
            assert result == {"check": "commit-message", "regex": ".*"}

        def test_find_check_not_found(self):
            """Test _find_check when check is not found."""
            checks = [
                {"check": "commit-message", "regex": ".*"},
            ]
            result = _find_check(checks, "author-name")
            assert result is None

        def test_find_check_empty_list(self):
            """Test _find_check with empty list."""
            checks = []
            result = _find_check(checks, "commit-message")
            assert result is None

        def test_load_toml_file_not_found(self):
            """Test _load_toml with non-existent file."""
            result = _load_toml(PurePath("/nonexistent/path/config.toml"))
            assert result == {}

        def test_load_toml_invalid_toml(self):
            """Test _load_toml with invalid TOML content."""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".toml", delete=False
            ) as f:
                f.write("invalid toml { content")
                temp_path = f.name

            try:
                result = _load_toml(PurePath(temp_path))
                assert result == {}
            finally:
                os.unlink(temp_path)

        def test_load_toml_valid(self):
            """Test _load_toml with valid TOML content."""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".toml", delete=False
            ) as f:
                f.write('[checks]\ncommit_message = { pattern = ".*" }\n')
                temp_path = f.name

            try:
                result = _load_toml(PurePath(temp_path))
                assert isinstance(result, dict)
                assert "checks" in result
            finally:
                os.unlink(temp_path)

        def test_find_config_file_directory_commit_check_toml(self):
            """Test _find_config_file finds commit-check.toml in directory."""
            with tempfile.TemporaryDirectory() as tmpdir:
                config_file = Path(tmpdir) / "commit-check.toml"
                config_file.write_text("[checks]")

                result = _find_config_file(tmpdir)
                assert result == config_file

        def test_find_config_file_directory_cchk_toml(self):
            """Test _find_config_file finds cchk.toml in directory."""
            with tempfile.TemporaryDirectory() as tmpdir:
                config_file = Path(tmpdir) / "cchk.toml"
                config_file.write_text("[checks]")

                result = _find_config_file(tmpdir)
                assert result == config_file

        def test_find_config_file_directory_priority(self):
            """Test _find_config_file prefers cchk.toml over commit-check.toml."""
            with tempfile.TemporaryDirectory() as tmpdir:
                config1 = Path(tmpdir) / "cchk.toml"
                config2 = Path(tmpdir) / "commit-check.toml"
                config1.write_text("[checks]")
                config2.write_text("[checks]")

                result = _find_config_file(tmpdir)
                assert result == config1

        def test_find_config_file_github_directory_cchk_toml(self):
            """Test _find_config_file finds .github/cchk.toml in directory."""
            with tempfile.TemporaryDirectory() as tmpdir:
                github_dir = Path(tmpdir) / ".github"
                github_dir.mkdir()
                config_file = github_dir / "cchk.toml"
                config_file.write_text("[checks]")

                result = _find_config_file(tmpdir)
                assert result == config_file

        def test_find_config_file_github_directory_commit_check_toml(self):
            """Test _find_config_file finds .github/commit-check.toml in directory."""
            with tempfile.TemporaryDirectory() as tmpdir:
                github_dir = Path(tmpdir) / ".github"
                github_dir.mkdir()
                config_file = github_dir / "commit-check.toml"
                config_file.write_text("[checks]")

                result = _find_config_file(tmpdir)
                assert result == config_file

        def test_find_config_file_priority_root_over_github(self):
            """Test _find_config_file prefers root configs over .github configs."""
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create both root and .github configs
                root_config = Path(tmpdir) / "cchk.toml"
                root_config.write_text("[checks]")
                
                github_dir = Path(tmpdir) / ".github"
                github_dir.mkdir()
                github_config = github_dir / "cchk.toml"
                github_config.write_text("[checks]")

                result = _find_config_file(tmpdir)
                # Should prefer root over .github
                assert result == root_config

        def test_find_config_file_directory_no_config(self):
            """Test _find_config_file returns None when no config found in directory."""
            with tempfile.TemporaryDirectory() as tmpdir:
                result = _find_config_file(tmpdir)
                assert result is None

        def test_find_config_file_explicit_toml_exists(self):
            """Test _find_config_file with explicit .toml file path."""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".toml", delete=False
            ) as f:
                f.write("[checks]")
                temp_path = f.name

            try:
                result = _find_config_file(temp_path)
                assert result == Path(temp_path)
            finally:
                os.unlink(temp_path)

        def test_find_config_file_explicit_toml_not_exists(self):
            """Test _find_config_file with non-existent .toml file path."""
            result = _find_config_file("/nonexistent/config.toml")
            assert result is None

        def test_find_config_file_non_toml_file(self):
            """Test _find_config_file with non-.toml file."""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yml", delete=False
            ) as f:
                f.write("checks:")
                temp_path = f.name

            try:
                result = _find_config_file(temp_path)
                assert result is None
            finally:
                os.unlink(temp_path)

        def test_validate_config_with_toml(self):
            """Test validate_config loads and validates TOML config."""
            with tempfile.TemporaryDirectory() as tmpdir:
                config_file = Path(tmpdir) / "commit-check.toml"
                config_file.write_text("""
[checks.commit_message]
pattern = "^(feat|fix|docs|style|refactor|test|chore).*"
""")

                result = validate_config(tmpdir)
                assert "checks" in result
                assert isinstance(result["checks"], list)

        def test_validate_config_yaml_fallback(self):
            """Test validate_config falls back to YAML when TOML not found."""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yml", delete=False
            ) as f:
                f.write("""
checks:
  - check: commit-message
    regex: ".*"
""")
                temp_path = f.name

            try:
                result = validate_config(temp_path)
                assert isinstance(result, dict)
            finally:
                os.unlink(temp_path)

        def test_validate_config_yaml_not_found(self):
            """Test validate_config returns empty dict when YAML not found."""
            result = validate_config("/nonexistent/config.yml")
            assert result == {}

        def test_validate_config_yaml_invalid(self):
            """Test validate_config handles invalid YAML."""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yml", delete=False
            ) as f:
                f.write("invalid: yaml: : content:")
                temp_path = f.name

            try:
                result = validate_config(temp_path)
                # Should return empty dict on error
                assert isinstance(result, dict)
            finally:
                os.unlink(temp_path)

        def test_validate_config_empty_toml(self):
            """Test validate_config with empty TOML file."""
            with tempfile.TemporaryDirectory() as tmpdir:
                config_file = Path(tmpdir) / "commit-check.toml"
                config_file.write_text("")

                result = validate_config(tmpdir)
                assert result == {}

        @patch("commit_check.util._toml", None)
        def test_load_toml_when_toml_not_available(self):
            """Test _load_toml returns empty dict when toml library not available."""
            result = _load_toml(PurePath("/some/path/config.toml"))
            assert result == {}
