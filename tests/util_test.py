import pytest
from commit_check.util import get_branch_name
from commit_check.util import get_commits_info
from commit_check.util import cmd_output
from commit_check.util import validate_config
from commit_check.util import print_error_message
from commit_check.util import print_suggestion
from subprocess import CalledProcessError, PIPE


class TestUtil:
    class TestGetBranchName:
        def test_get_branch_name(self, mocker):
            # Must call cmd_output with given argument.
            m_cmd_output = mocker.patch(
                "commit_check.util.cmd_output",
                return_value=" fake_branch_name "
            )
            retval = get_branch_name()
            assert m_cmd_output.call_count == 1
            assert m_cmd_output.call_args[0][0] == [
                "git", "rev-parse", "--abbrev-ref", "HEAD"
            ]
            assert retval == "fake_branch_name"

        def test_get_branch_name_with_exception(self, mocker):
            # Must return empty string when exception raises in cmd_output.
            m_cmd_output = mocker.patch(
                "commit_check.util.cmd_output",
                return_value=" fake_branch_name "
            )
            # CalledProcessError's args also dummy
            dummy_ret_code, dummy_cmd_name = 1, "dcmd"
            m_cmd_output.side_effect = CalledProcessError(
                dummy_ret_code,
                dummy_cmd_name
            )
            retval = get_branch_name()
            assert m_cmd_output.call_count == 1
            assert m_cmd_output.call_args[0][0] == [
                "git", "rev-parse", "--abbrev-ref", "HEAD"
            ]
            assert retval == ""

    class TestGetCommitInfo:
        @pytest.mark.parametrize("format_string", [
            ("s"),
            ("an"),
            ("ae"),
        ]
        )
        def test_get_commits_info(self, mocker, format_string):
            # Must call get_commits_info with given argument.
            m_cmd_output = mocker.patch(
                "commit_check.util.cmd_output",
                return_value=" fake commit message "
            )
            retval = get_commits_info(format_string)
            assert m_cmd_output.call_count == 1
            assert m_cmd_output.call_args[0][0] == [
                "git", "log", "-n", "1", f"--pretty=format:%{format_string}"
            ]
            assert retval == " fake commit message "

        def test_get_commits_info_with_exception(self, mocker):
            # Must return empty string when exception raises in cmd_output.
            m_cmd_output = mocker.patch(
                "commit_check.util.cmd_output",
                return_value=" fake commit message "
            )
            # CalledProcessError's args also dummy
            dummy_ret_code, dummy_cmd_name = 1, "dcmd"
            m_cmd_output.side_effect = CalledProcessError(
                dummy_ret_code,
                dummy_cmd_name
            )
            format_string = "s"
            retval = get_commits_info(format_string)
            assert m_cmd_output.call_count == 1
            assert m_cmd_output.call_args[0][0] == [
                "git", "log", "-n", "1", f"--pretty=format:%{format_string}"
            ]
            assert retval == ""

    class TestCmdOutput:
        # use DummyProcessResult in this test to access returncode, stdout and stderr attribute
        class DummyProcessResult:
            def __init__(self, returncode, stdout, stderr):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def test_cmd_output(self, mocker):
            # Must subprocess.run with given argument.
            m_subprocess_run = mocker.patch(
                "subprocess.run",
                return_value=self.DummyProcessResult(0, "ok", "")
            )
            retval = cmd_output(["dummy_cmd"])
            assert m_subprocess_run.call_count == 1
            assert retval == "ok"

        @pytest.mark.parametrize("returncode, stdout, stderr", [
            (1, "ok", "err"),
            (0, None, "err"),
            (1, None, "err"),
        ]
        )
        def test_cmd_output_err(self, mocker, returncode, stdout, stderr):
            # Must return stderr when  subprocess.run returns not empty stderr.
            m_subprocess_run = mocker.patch(
                "subprocess.run",
                return_value=self.DummyProcessResult(
                    returncode, stdout, stderr)
            )
            dummy_cmd = ["dummy_cmd"]
            retval = cmd_output(dummy_cmd)
            assert m_subprocess_run.call_count == 1
            assert retval == stderr
            assert m_subprocess_run.call_args[0][0] == dummy_cmd
            assert m_subprocess_run.call_args[1] == {
                'encoding': 'utf-8',
                'stderr': PIPE,
                "stdout": PIPE
            }

        @pytest.mark.parametrize("returncode, stdout, stderr", [
            (1, "ok", ""),
            (0, None, ""),
            (1, None, ""),
        ]
        )
        def test_cmd_output_err_with_len0_stderr(self, mocker, returncode, stdout, stderr):
            # Must return empty string when subprocess.run returns empty stderr.
            m_subprocess_run = mocker.patch(
                "subprocess.run",
                return_value=self.DummyProcessResult(
                    returncode, stdout, stderr)
            )
            dummy_cmd = ["dummy_cmd"]
            retval = cmd_output(dummy_cmd)
            assert m_subprocess_run.call_count == 1
            assert retval == ""
            assert m_subprocess_run.call_args[0][0] == dummy_cmd
            assert m_subprocess_run.call_args[1] == {
                'encoding': 'utf-8',
                'stderr': PIPE,
                "stdout": PIPE
            }

    class TestValidateConfig:
        def test_validate_config(self, mocker):
            # Must call yaml.safe_load.
            mocker.patch("builtins.open")
            dummy_resp = {"key": "value"}
            m_yaml_safe_load = mocker.patch(
                "yaml.safe_load",
                return_value=dummy_resp
            )
            retval = validate_config("dummy_path")
            assert m_yaml_safe_load.call_count == 1
            assert retval == dummy_resp

        def test_validate_config_file_not_found(self, mocker):
            # Must return empty dictionary when FileNotFoundError raises in built-in open.
            mocker.patch("builtins.open").side_effect = FileNotFoundError
            m_yaml_safe_load = mocker.patch("yaml.safe_load")
            retval = validate_config("dummy_path")
            assert m_yaml_safe_load.call_count == 0
            assert retval == {}

    class TestPrintErrorMessage:
        @pytest.mark.parametrize("check_type, type_failed_msg", [
            ("message", "check failed =>"),
            ("branch", "check failed =>"),
            ("author_name", "check failed =>"),
            ("author_email", "check failed =>"),
            ("commit_signoff", "check failed =>"),
        ])
        def test_print_error_message(self, capfd, check_type, type_failed_msg):
            # Must print on stdout with given argument.
            dummy_regex = "dummy regex"
            dummy_reason = "failure reason"
            dummy_error = "dummy error"
            print_error_message(
                check_type,
                dummy_regex,
                dummy_error,
                dummy_reason
            )
            stdout, _ = capfd.readouterr()
            assert "Commit rejected by Commit-Check" in stdout
            assert "Commit rejected." in stdout
            assert check_type in stdout
            assert type_failed_msg in stdout
            assert f"It doesn't match regex: {dummy_regex}" in stdout
            assert dummy_error in stdout

    class TestPrintSuggestion:
        def test_print_suggestion(self, capfd):
            # Must print on stdout with given argument.
            print_suggestion("dummy suggest")
            stdout, _ = capfd.readouterr()
            assert "Suggest:" in stdout

        def test_print_suggestion_exit1(self, capfd):
            # Must exit with 1 when "" passed
            with pytest.raises(SystemExit) as e:
                print_suggestion("")
            assert e.value.code == 1
            stdout, _ = capfd.readouterr()
            assert "commit-check does not support" in stdout
