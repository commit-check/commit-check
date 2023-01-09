import pytest
from commit_check.util import (get_branch_name,
                               get_commits_info,
                               cmd_output,
                               validate_config,
                               print_error_message,
                               print_suggestion)
from subprocess import CalledProcessError, PIPE


class TestUtil:
    class TestGetBranchName:
        def test_get_branch_name(self, mocker):
            # Must call cmd_output with gived argument.
            m_cmd_output = mocker.patch(
                "commit_check.util.cmd_output",
                return_value=" fake_branch_name "
            )

            res = get_branch_name()

            assert m_cmd_output.call_count == 1
            assert m_cmd_output.call_args[0][0] == [
                "git", "rev-parse", "--abbrev-ref", "HEAD"
            ]
            assert res == "fake_branch_name"

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

            res = get_branch_name()

            assert m_cmd_output.call_count == 1
            assert m_cmd_output.call_args[0][0] == [
                "git", "rev-parse", "--abbrev-ref", "HEAD"
            ]
            assert res == ""

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

            res = get_commits_info(format_string)

            assert m_cmd_output.call_count == 1
            assert m_cmd_output.call_args[0][0] == [
                "git", "log", "-n", "1", f"--pretty=format:%{format_string}"
            ]
            assert res == " fake commit message "

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
            res = get_commits_info(format_string)

            assert m_cmd_output.call_count == 1
            assert m_cmd_output.call_args[0][0] == [
                "git", "log", "-n", "1", f"--pretty=format:%{format_string}"
            ]
            assert res == ""

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

            res = cmd_output(["dummy_cmd"])

            assert m_subprocess_run.call_count == 1
            assert res == "ok"

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
            res = cmd_output(dummy_cmd)

            assert m_subprocess_run.call_count == 1
            assert res == stderr
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
            # Must return empty string when  subprocess.run returns empty stderr.
            m_subprocess_run = mocker.patch(
                "subprocess.run",
                return_value=self.DummyProcessResult(
                    returncode, stdout, stderr)
            )

            dummy_cmd = ["dummy_cmd"]
            res = cmd_output(dummy_cmd)

            assert m_subprocess_run.call_count == 1
            assert res == ""
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

            res = validate_config("dummy_path")

            assert m_yaml_safe_load.call_count == 1
            assert res == dummy_resp

        def test_validate_config_file_not_found(self, mocker):
            # Must return empty dictionary when FileNotFoundError raises in built-in open.
            mocker.patch("builtins.open").side_effect = FileNotFoundError
            m_yaml_safe_load = mocker.patch("yaml.safe_load")

            res = validate_config("dummy_path")

            assert m_yaml_safe_load.call_count == 0
            assert res == {}

    class TestPrintErrorMessage:
        @pytest.mark.parametrize("check_type, invalid_type_msg", [
            ("commit_message", "Invalid commit message"),
            ("branch_name", "Invalid branch name"),
            ("author_name", "Invalid author name"),
            ("author_email", "Invalid email address"),
        ])
        def test_print_error_message(self, capfd, check_type, invalid_type_msg):
            # Must print on stdout with given argument.

            dummy_regex = "dummy regex"
            dummy_error_point = "error point"
            dummy_error = "dummy error"
            print_error_message(
                check_type,
                dummy_regex,
                dummy_error,
                dummy_error_point
            )
            stdout, _ = capfd.readouterr()
            assert "Commit rejected by Commit-Check" in stdout
            assert "Commit rejected." in stdout
            assert invalid_type_msg in stdout
            assert f"It doesn't match regex: {dummy_regex}" in stdout
            assert dummy_error in stdout

        def test_print_error_message_exit1(self, capfd):
            # Must exit with 1 when not supported check type passed.
            with pytest.raises(SystemExit) as e:
                print_error_message(
                    "not_supported_check_type",
                    "",
                    "",
                    "not supported check type error"
                )
            assert e.value.code == 1
            stdout, _ = capfd.readouterr()
            assert "Commit rejected by Commit-Check" in stdout
            assert "Commit rejected." in stdout
            assert "commit-check does not support" in stdout

    class TestPrintSuggestion:
        def test_print_suggestion(self, capfd):
            # Must print on stdout with given argument.
            print_suggestion("dummy suggest")
            stdout, _ = capfd.readouterr()
            assert "Suggest to run" in stdout

        def test_print_suggestion_exit1(self, capfd):
            # Must exit with 1 when None passed
            with pytest.raises(SystemExit) as e:
                print_suggestion(None)

            assert e.value.code == 1
            stdout, _ = capfd.readouterr()
            assert "commit-check does not support" in stdout
