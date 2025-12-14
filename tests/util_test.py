import pytest
import subprocess
from commit_check.util import get_branch_name
from commit_check.util import has_commits
from commit_check.util import git_merge_base
from commit_check.util import get_commit_info
from commit_check.util import cmd_output
from commit_check.util import print_error_header
from commit_check.util import print_error_message
from commit_check.util import print_suggestion
from commit_check.util import _find_check
from commit_check.util import _print_failure
from commit_check.util import _find_config_file
from commit_check.util import _load_toml
from commit_check.util import validate_config
from subprocess import CalledProcessError, PIPE
from unittest.mock import MagicMock
from unittest.mock import patch


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


# Additional coverage tests
class TestFindCheck:
    """Test the _find_check function."""

    def test_find_check_with_matching_type(self):
        """Test finding a check by type."""
        checks = [
            {"check": "message", "regex": ".*"},
            {"check": "branch", "regex": ".*"},
        ]
        result = _find_check(checks, "branch")
        assert result == {"check": "branch", "regex": ".*"}

    def test_find_check_with_no_match(self):
        """Test when no check matches."""
        checks = [{"check": "message", "regex": ".*"}]
        result = _find_check(checks, "author_name")
        assert result is None


class TestPrintFailure:
    """Test the _print_failure function."""

    def test_print_failure_first_call_prints_header(self, capsys):
        """Test that header is printed on first failure."""
        print_error_header.has_been_called = False
        check = {"check": "message", "error": "Invalid format", "suggest": "Use feat:"}
        _print_failure(check, "^feat:.*", "wrong message")

        captured = capsys.readouterr()
        assert "Commit rejected" in captured.out
        assert "check failed ==>" in captured.out
        assert "Suggest:" in captured.out

    def test_print_failure_subsequent_call_no_header(self, capsys):
        """Test that header is not printed on subsequent failures."""
        print_error_header.has_been_called = True
        check = {"check": "branch", "error": "Invalid branch"}
        _print_failure(check, "^feature/.*", "wrong-branch")

        captured = capsys.readouterr()
        assert "CHECK" not in captured.out
        assert "check failed ==>" in captured.out


class TestPrintSuggestionEdgeCases:
    """Test print_suggestion error paths."""

    def test_print_suggestion_with_none_raises_system_exit(self, capsys):
        """Test that None suggestion raises SystemExit."""
        with pytest.raises(SystemExit) as exc_info:
            print_suggestion(None)
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "commit-check does not support" in captured.out


class TestTomlLoading:
    """Test TOML loading edge cases."""

    def test_load_toml_with_nonexistent_file(self, tmp_path):
        """Test loading TOML from nonexistent file."""
        nonexistent = tmp_path / "does_not_exist.toml"
        result = _load_toml(nonexistent)
        assert result == {}

    def test_load_toml_with_invalid_toml(self, tmp_path):
        """Test loading invalid TOML file."""
        invalid_toml = tmp_path / "invalid.toml"
        invalid_toml.write_text("this is not valid toml ][")
        result = _load_toml(invalid_toml)
        assert result == {}

    @patch("commit_check.util._toml", None)
    def test_load_toml_without_toml_module(self, tmp_path):
        """Test loading TOML when toml module is not available."""
        valid_toml = tmp_path / "valid.toml"
        valid_toml.write_text("[commit]\nconventional_commits = true")
        result = _load_toml(valid_toml)
        assert result == {}


class TestFindConfigFile:
    """Test config file finding logic."""

    def test_find_config_file_in_directory_commit_check_toml(self, tmp_path):
        """Test finding commit-check.toml in directory."""
        config_file = tmp_path / "commit-check.toml"
        config_file.write_text("[commit]")
        result = _find_config_file(str(tmp_path))
        assert result == config_file

    def test_find_config_file_in_directory_cchk_toml(self, tmp_path):
        """Test finding cchk.toml when commit-check.toml doesn't exist."""
        config_file = tmp_path / "cchk.toml"
        config_file.write_text("[commit]")
        result = _find_config_file(str(tmp_path))
        assert result == config_file

    def test_find_config_file_priority(self, tmp_path):
        """Test that commit-check.toml has priority over cchk.toml."""
        commit_check_file = tmp_path / "commit-check.toml"
        cchk_file = tmp_path / "cchk.toml"
        commit_check_file.write_text("[commit]")
        cchk_file.write_text("[branch]")
        result = _find_config_file(str(tmp_path))
        assert result == commit_check_file

    def test_find_config_file_explicit_toml_path(self, tmp_path):
        """Test finding explicitly specified TOML file."""
        config_file = tmp_path / "custom.toml"
        config_file.write_text("[commit]")
        result = _find_config_file(str(config_file))
        assert result == config_file

    def test_find_config_file_nonexistent_explicit_path(self, tmp_path):
        """Test with nonexistent explicit file path."""
        nonexistent = tmp_path / "nonexistent.toml"
        result = _find_config_file(str(nonexistent))
        assert result is None

    def test_find_config_file_non_toml_extension(self, tmp_path):
        """Test with non-TOML file extension."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("commit: {}")
        result = _find_config_file(str(yaml_file))
        assert result is None

    def test_find_config_file_empty_directory(self, tmp_path):
        """Test finding config in empty directory."""
        result = _find_config_file(str(tmp_path))
        assert result is None


class TestValidateConfigYamlFallback:
    """Test validate_config YAML fallback paths."""

    def test_validate_config_with_yaml_fallback(self, tmp_path):
        """Test YAML fallback when TOML not found."""
        yaml_file = tmp_path / "config.yml"
        yaml_file.write_text("checks:\n  - check: message\n    regex: .*")
        result = validate_config(str(yaml_file))
        assert "checks" in result
        assert len(result["checks"]) > 0

    def test_validate_config_yaml_not_found(self, tmp_path):
        """Test YAML fallback with nonexistent file."""
        nonexistent = tmp_path / "nonexistent.yml"
        result = validate_config(str(nonexistent))
        assert result == {}

    def test_validate_config_invalid_yaml(self, tmp_path):
        """Test YAML fallback with invalid YAML."""
        invalid_yaml = tmp_path / "invalid.yml"
        invalid_yaml.write_text("invalid: yaml: content: [")
        result = validate_config(str(invalid_yaml))
        assert result == {}

    def test_validate_config_empty_yaml(self, tmp_path):
        """Test YAML fallback with empty file."""
        empty_yaml = tmp_path / "empty.yml"
        empty_yaml.write_text("")
        result = validate_config(str(empty_yaml))
        assert result == {}
