import importlib
import os
import sys
import pytest
import subprocess
import commit_check
from commit_check import supports_color
from commit_check.util import (
    get_tags_at,
    get_commit_files,
    parse_size,
    format_size,
    fetch_remote_ref,
    fetch_upstream_ref,
    get_branch_name,
    get_git_remotes,
    get_remote_branch_sha,
    get_upstream_branch,
    get_upstream_remote_sha,
    has_commits,
    git_merge_base,
    get_commit_info,
    cmd_output,
    print_error_header,
    print_error_message,
    print_suggestion,
    supports_hyperlinks,
    hyperlink,
    _print_failure,
)
from subprocess import CalledProcessError, PIPE
from unittest.mock import MagicMock

# String constants used across tests
REFS_HEADS_MAIN = "refs/heads/main"
USER_NAME_CONFIG = "user.name"


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

    class TestGetUpstreamBranch:
        @pytest.mark.benchmark
        def test_get_upstream_branch(self, mocker):
            mock_run = mocker.patch(
                "subprocess.run",
                return_value=type(
                    "MockResult",
                    (),
                    {"stdout": "origin/main\n", "stderr": "", "returncode": 0},
                )(),
            )

            result = get_upstream_branch()

            mock_run.assert_called_once_with(
                [
                    "git",
                    "rev-parse",
                    "--abbrev-ref",
                    "--symbolic-full-name",
                    "@{upstream}",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
            )
            assert result == "origin/main"

        @pytest.mark.benchmark
        def test_get_upstream_branch_missing(self, mocker):
            mocker.patch(
                "subprocess.run",
                return_value=type(
                    "MockResult",
                    (),
                    {
                        "stdout": "",
                        "stderr": "fatal: no upstream",
                        "returncode": 128,
                    },
                )(),
            )

            assert get_upstream_branch() == ""

    class TestGetUpstreamRemoteSha:
        @pytest.mark.benchmark
        def test_get_upstream_remote_sha(self, mocker):
            mock_run = mocker.patch(
                "subprocess.run",
                return_value=type(
                    "MockResult",
                    (),
                    {
                        "stdout": "abc123\trefs/heads/main\n",
                        "stderr": "",
                        "returncode": 0,
                    },
                )(),
            )

            result = get_upstream_remote_sha("origin/main")

            mock_run.assert_called_once_with(
                ["git", "ls-remote", "--exit-code", "origin", REFS_HEADS_MAIN],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
            )
            assert result == "abc123"

        @pytest.mark.benchmark
        def test_get_upstream_remote_sha_with_nested_branch(self, mocker):
            mocker.patch(
                "subprocess.run",
                return_value=type(
                    "MockResult",
                    (),
                    {
                        "stdout": "def456\trefs/heads/feature/topic\n",
                        "stderr": "",
                        "returncode": 0,
                    },
                )(),
            )

            assert get_upstream_remote_sha("origin/feature/topic") == "def456"

        @pytest.mark.benchmark
        def test_get_upstream_remote_sha_missing(self, mocker):
            mocker.patch(
                "subprocess.run",
                return_value=type(
                    "MockResult",
                    (),
                    {"stdout": "", "stderr": "fatal", "returncode": 2},
                )(),
            )

            assert get_upstream_remote_sha("origin/main") == ""

        @pytest.mark.benchmark
        def test_get_upstream_remote_sha_invalid_ref(self, mocker):
            mock_run = mocker.patch("subprocess.run")

            assert get_upstream_remote_sha("main") == ""
            mock_run.assert_not_called()

    class TestGetRemoteBranchSha:
        @pytest.mark.benchmark
        def test_get_remote_branch_sha(self, mocker):
            mock_run = mocker.patch(
                "subprocess.run",
                return_value=type(
                    "MockResult",
                    (),
                    {
                        "stdout": "abc123\trefs/heads/main\n",
                        "stderr": "",
                        "returncode": 0,
                    },
                )(),
            )

            result = get_remote_branch_sha("origin", "main")

            mock_run.assert_called_once_with(
                ["git", "ls-remote", "--exit-code", "origin", REFS_HEADS_MAIN],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
            )
            assert result == "abc123"

        @pytest.mark.benchmark
        @pytest.mark.parametrize(
            "remote_name,branch_name",
            [
                ("", "main"),
                ("origin", ""),
            ],
        )
        def test_get_remote_branch_sha_invalid_args(
            self, mocker, remote_name, branch_name
        ):
            mock_run = mocker.patch("subprocess.run")

            assert get_remote_branch_sha(remote_name, branch_name) == ""
            mock_run.assert_not_called()

    class TestFetchUpstreamRef:
        @pytest.mark.benchmark
        def test_fetch_upstream_ref(self, mocker):
            mock_run = mocker.patch(
                "subprocess.run",
                return_value=type(
                    "MockResult",
                    (),
                    {"stdout": "", "stderr": "", "returncode": 0},
                )(),
            )

            assert fetch_upstream_ref("origin/main") is True
            mock_run.assert_called_once_with(
                ["git", "fetch", "--quiet", "--no-tags", "origin", "main"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
            )

        @pytest.mark.benchmark
        def test_fetch_upstream_ref_failure(self, mocker):
            mocker.patch(
                "subprocess.run",
                return_value=type(
                    "MockResult",
                    (),
                    {"stdout": "", "stderr": "fatal", "returncode": 1},
                )(),
            )

            assert fetch_upstream_ref("origin/main") is False

        @pytest.mark.benchmark
        def test_fetch_upstream_ref_invalid_ref(self, mocker):
            mock_run = mocker.patch("subprocess.run")

            assert fetch_upstream_ref("main") is False
            mock_run.assert_not_called()

    class TestGetGitRemotes:
        @pytest.mark.benchmark
        def test_get_git_remotes(self, mocker):
            mocker.patch(
                "subprocess.run",
                return_value=type(
                    "MockResult",
                    (),
                    {"stdout": "origin\nupstream\n", "stderr": "", "returncode": 0},
                )(),
            )

            assert get_git_remotes() == ["origin", "upstream"]

        @pytest.mark.benchmark
        def test_get_git_remotes_failure(self, mocker):
            mocker.patch(
                "subprocess.run",
                return_value=type(
                    "MockResult",
                    (),
                    {"stdout": "", "stderr": "fatal", "returncode": 128},
                )(),
            )

            assert get_git_remotes() == []

    class TestFetchRemoteRef:
        @pytest.mark.benchmark
        def test_fetch_remote_ref(self, mocker):
            mock_run = mocker.patch(
                "subprocess.run",
                return_value=type(
                    "MockResult",
                    (),
                    {"stdout": "", "stderr": "", "returncode": 0},
                )(),
            )

            assert fetch_remote_ref("origin", REFS_HEADS_MAIN) is True
            mock_run.assert_called_once_with(
                ["git", "fetch", "--quiet", "--no-tags", "origin", REFS_HEADS_MAIN],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
            )

        @pytest.mark.benchmark
        def test_fetch_remote_ref_failure(self, mocker):
            mocker.patch(
                "subprocess.run",
                return_value=type(
                    "MockResult",
                    (),
                    {"stdout": "", "stderr": "fatal", "returncode": 1},
                )(),
            )

            assert fetch_remote_ref("origin", REFS_HEADS_MAIN) is False

        @pytest.mark.benchmark
        @pytest.mark.parametrize(
            "remote_name,remote_ref",
            [
                ("", REFS_HEADS_MAIN),
                ("origin", ""),
            ],
        )
        def test_fetch_remote_ref_invalid_args(self, mocker, remote_name, remote_ref):
            mock_run = mocker.patch("subprocess.run")

            assert fetch_remote_ref(remote_name, remote_ref) is False
            mock_run.assert_not_called()

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
            "check_type, printed_name",
            [
                ("message", "message"),
                ("branch", "branch"),
                # The config key is snake_case, but the rules reference titles
                # its sections in kebab-case. The output follows the reference,
                # so a name read here can be searched for there verbatim.
                ("author_name", "author-name"),
                ("author_email", "author-email"),
                ("signoff", "signoff"),
            ],
        )
        @pytest.mark.benchmark
        def test_print_error_message(self, capfd, check_type, printed_name):
            # Must print on stdout with given argument.
            dummy_reason = "failure reason"
            dummy_error = "dummy error"
            print_error_message(check_type, dummy_error, dummy_reason)
            stdout, _ = capfd.readouterr()
            assert printed_name in stdout
            assert "_" not in stdout.split(" check failed")[0]
            assert "check failed ==>" in stdout
            assert dummy_error in stdout

    class TestHyperlinks:
        """The rule ID doubles as a link to its documentation.

        Only where that renders: a terminal that does not understand OSC 8 may
        print the escape payload as visible junk, and in a CI log the sequence
        is noise around a URL the reader can no longer click anyway.
        """

        @pytest.mark.benchmark
        def test_hyperlink_wraps_text_in_osc8(self):
            assert hyperlink("CC001", "https://example.com/#cc001") == (
                "\033]8;;https://example.com/#cc001\033\\CC001\033]8;;\033\\"
            )

        @pytest.mark.benchmark
        def test_not_supported_when_piped(self, mocker):
            mocker.patch.dict("os.environ", {}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=False)
            assert supports_hyperlinks() is False

        @pytest.mark.benchmark
        def test_forced_even_when_piped(self, mocker):
            mocker.patch.dict("os.environ", {"FORCE_HYPERLINK": "1"}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=False)
            assert supports_hyperlinks() is True

        @pytest.mark.benchmark
        def test_force_zero_turns_links_off(self, mocker):
            """Setting it to 0 must not read as "set, therefore on"."""
            mocker.patch.dict(
                "os.environ",
                {"FORCE_HYPERLINK": "0", "TERM_PROGRAM": "WezTerm"},
                clear=True,
            )
            mocker.patch("sys.stdout.isatty", return_value=True)
            assert supports_hyperlinks() is False

        @pytest.mark.benchmark
        def test_force_empty_falls_through_to_detection(self, mocker):
            mocker.patch.dict("os.environ", {"FORCE_HYPERLINK": ""}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=False)
            assert supports_hyperlinks() is False

        @pytest.mark.benchmark
        @pytest.mark.parametrize(
            "env, expected",
            [
                ({"TERM_PROGRAM": "WezTerm"}, True),
                ({"TERM_PROGRAM": "iTerm.app"}, True),
                ({"TERM_PROGRAM": "vscode"}, True),
                ({"TERM": "xterm-kitty"}, True),
                ({"VTE_VERSION": "6003"}, True),
                ({"VTE_VERSION": "4000"}, False),
                # Malformed rather than absent; must not raise.
                ({"VTE_VERSION": "not-a-number"}, False),
                ({"TERM": "xterm"}, False),
                ({"TERM": "dumb", "TERM_PROGRAM": "WezTerm"}, False),
            ],
        )
        def test_terminal_detection(self, mocker, env, expected):
            mocker.patch.dict("os.environ", env, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=True)
            assert supports_hyperlinks() is expected

        @pytest.mark.benchmark
        def test_id_is_linked_when_supported(self, capfd, mocker):
            mocker.patch("commit_check.util.supports_hyperlinks", return_value=True)
            print_error_message(
                "subject_min_length",
                "too short",
                "hi",
                rule_id="CC005",
                docs_url="https://commit-check.com/rules/#cc005",
            )
            stdout, _ = capfd.readouterr()
            assert "\033]8;;https://commit-check.com/rules/#cc005\033\\" in stdout

        @pytest.mark.benchmark
        def test_id_is_plain_when_unsupported(self, capfd, mocker):
            mocker.patch("commit_check.util.supports_hyperlinks", return_value=False)
            print_error_message(
                "subject_min_length",
                "too short",
                "hi",
                rule_id="CC005",
                docs_url="https://commit-check.com/rules/#cc005",
            )
            stdout, _ = capfd.readouterr()
            assert "\033]8;;" not in stdout
            assert "CC005" in stdout

        @pytest.mark.benchmark
        def test_docs_line_kept_without_hyperlinks(self, capfd, mocker):
            """A CI log is where the printed URL is the only way to reach it."""
            mocker.patch("commit_check.util.supports_hyperlinks", return_value=False)
            _print_failure(
                {
                    "check": "subject_min_length",
                    "error": "too short",
                    "suggest": "write more",
                    "rule_id": "CC005",
                    "docs_url": "https://commit-check.com/rules/#cc005",
                },
                "hi",
                no_banner=True,
            )
            stdout, _ = capfd.readouterr()
            assert "Docs: https://commit-check.com/rules/#cc005" in stdout

        @pytest.mark.benchmark
        def test_docs_line_dropped_when_id_is_the_link(self, capfd, mocker):
            """Otherwise every failure spends a line repeating its own link."""
            mocker.patch("commit_check.util.supports_hyperlinks", return_value=True)
            _print_failure(
                {
                    "check": "subject_min_length",
                    "error": "too short",
                    "suggest": "write more",
                    "rule_id": "CC005",
                    "docs_url": "https://commit-check.com/rules/#cc005",
                },
                "hi",
                no_banner=True,
            )
            stdout, _ = capfd.readouterr()
            assert "Docs: " not in stdout
            assert "\033]8;;" in stdout

        @pytest.mark.benchmark
        def test_blank_line_closes_the_block(self, capfd, mocker):
            """The separator belongs between rules, not inside one."""
            mocker.patch("commit_check.util.supports_hyperlinks", return_value=False)
            _print_failure(
                {
                    "check": "subject_min_length",
                    "error": "too short",
                    "suggest": "write more",
                    "rule_id": "CC005",
                    "docs_url": "https://commit-check.com/rules/#cc005",
                },
                "hi",
                no_banner=True,
            )
            stdout, _ = capfd.readouterr()
            lines = stdout.splitlines()
            assert lines[-1] == ""
            assert lines[-2].startswith("Docs: ")
            assert "" not in lines[:-1]

    class TestColor:
        """ANSI color belongs on a terminal, not in piped output.

        A CI log or an agent harness reads the escape payload as noise, so the
        color codes are dropped when ``stdout`` is not a terminal.
        """

        @pytest.fixture
        def restored_module(self):
            """Re-derive the module constants after a test that reloads.

            A reload recomputes ``commit_check.RED`` and friends under the
            test's patched environment, and nothing else puts them back: the
            last reload's values would leak into every test that runs
            afterwards. Listed before ``mocker`` in the signature so this
            teardown runs after the environment patches are undone.
            """
            yield
            importlib.reload(commit_check)

        @pytest.mark.benchmark
        def test_not_supported_when_piped(self, mocker):
            mocker.patch.dict("os.environ", {}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=False)
            assert supports_color() is False

        @pytest.mark.benchmark
        def test_no_color_turns_color_off_on_a_tty(self, mocker):
            """NO_COLOR is what users export globally (https://no-color.org)."""
            mocker.patch.dict("os.environ", {"NO_COLOR": "1"}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=True)
            assert supports_color() is False

        @pytest.mark.benchmark
        def test_no_color_empty_falls_through_to_detection(self, mocker):
            """The convention counts only a non-empty value as set."""
            mocker.patch.dict("os.environ", {"NO_COLOR": ""}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=True)
            assert supports_color() is True

        @pytest.mark.benchmark
        def test_force_color_outranks_no_color(self, mocker):
            """An explicit force wins over the global opt-out."""
            mocker.patch.dict(
                "os.environ", {"NO_COLOR": "1", "FORCE_COLOR": "1"}, clear=True
            )
            mocker.patch("sys.stdout.isatty", return_value=False)
            assert supports_color() is True

        @pytest.mark.benchmark
        def test_forced_even_when_piped(self, mocker):
            mocker.patch.dict("os.environ", {"FORCE_COLOR": "1"}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=False)
            assert supports_color() is True

        @pytest.mark.benchmark
        def test_force_zero_turns_color_off(self, mocker):
            """Setting it to 0 must not read as "set, therefore on"."""
            mocker.patch.dict("os.environ", {"FORCE_COLOR": "0"}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=True)
            assert supports_color() is False

        @pytest.mark.benchmark
        def test_force_empty_falls_through_to_detection(self, mocker):
            mocker.patch.dict("os.environ", {"FORCE_COLOR": ""}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=False)
            assert supports_color() is False

        @pytest.mark.benchmark
        def test_dumb_term_turns_color_off(self, mocker):
            mocker.patch.dict("os.environ", {"TERM": "dumb"}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=True)
            assert supports_color() is False

        @pytest.mark.benchmark
        def test_empty_term_turns_color_off(self, mocker):
            """``TERM=`` is a deliberate "no terminal" signal, like ``dumb``."""
            mocker.patch.dict("os.environ", {"TERM": ""}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=True)
            assert supports_color() is False

        @pytest.mark.benchmark
        def test_unset_term_still_allows_color_on_a_tty(self, mocker):
            """An absent TERM is not a refusal — the terminal may still render."""
            mocker.patch.dict("os.environ", {}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=True)
            assert supports_color() is True

        @pytest.mark.benchmark
        def test_constants_empty_when_color_off(self, restored_module, mocker):
            """The constants are pre-emptied when stdout cannot render color."""
            mocker.patch.dict("os.environ", {"TERM": "dumb"}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=True)
            importlib.reload(commit_check)
            assert commit_check.RED == ""
            assert commit_check.GREEN == ""
            assert commit_check.YELLOW == ""
            assert commit_check.RESET_COLOR == ""

        @pytest.mark.benchmark
        def test_constants_set_when_color_on(self, restored_module, mocker):
            """FORCE_COLOR=1 keeps the raw escape codes in place."""
            mocker.patch.dict("os.environ", {"FORCE_COLOR": "1"}, clear=True)
            mocker.patch("sys.stdout.isatty", return_value=False)
            importlib.reload(commit_check)
            assert commit_check.RED == "\033[91m"
            assert commit_check.GREEN == "\033[92m"
            assert commit_check.YELLOW == "\033[93m"
            assert commit_check.RESET_COLOR == "\033[0m"

        # Not benchmarked: these spawn an interpreter, and their cost is the
        # process, not the code under test.

        def test_the_decision_reaches_printed_output(self):
            """FORCE_COLOR=1 must colour what the print path emits.

            The reload tests above stop at the module constants, but the print
            functions in ``commit_check.util`` hold their own copies, bound
            once at import. Only a fresh interpreter exercises that hand-off,
            so this is the test that fails if the decision stops reaching the
            output a user sees.
            """
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from commit_check.util import print_error_message;"
                    "print_error_message('message', 'err', 'value', rule_id='CC001')",
                ],
                capture_output=True,
                encoding="utf-8",
                env={**os.environ, "FORCE_COLOR": "1"},
            )
            assert result.returncode == 0, result.stderr
            assert "\033[91m" in result.stdout

        #: Child program that pretends its stdout is a terminal before the
        #: import, so terminal detection says yes and the environment becomes
        #: the deciding factor. A plain pipe would disable color on its own
        #: and mask whether NO_COLOR handling exists at all.
        _TTY_CHILD = (
            "import sys, types;"
            "out = sys.stdout;"
            "sys.stdout = types.SimpleNamespace("
            "write=out.write, flush=out.flush, isatty=lambda: True);"
            "from commit_check.util import print_error_message;"
            "print_error_message('message', 'err', 'value', rule_id='CC001')"
        )

        def test_no_color_reaches_printed_output(self):
            """NO_COLOR must be what decides, not the pipe.

            Two identical runs, differing only in ``NO_COLOR``. The first
            proves the pretend-TTY works — it must come out colored, or the
            second assertion would pass even with the NO_COLOR handling
            deleted.
            """
            env = {**os.environ, "TERM": "xterm"}
            env.pop("FORCE_COLOR", None)
            env.pop("NO_COLOR", None)

            colored = subprocess.run(
                [sys.executable, "-c", self._TTY_CHILD],
                capture_output=True,
                encoding="utf-8",
                env=env,
            )
            assert colored.returncode == 0, colored.stderr
            assert "\033[" in colored.stdout

            plain = subprocess.run(
                [sys.executable, "-c", self._TTY_CHILD],
                capture_output=True,
                encoding="utf-8",
                env={**env, "NO_COLOR": "1"},
            )
            assert plain.returncode == 0, plain.stderr
            assert "\033[" not in plain.stdout

    class TestPrintSuggestion:
        @pytest.mark.benchmark
        def test_print_suggestion(self, capfd):
            # Must print on stdout with given argument.
            print_suggestion("dummy suggest")
            stdout, _ = capfd.readouterr()
            assert "Suggest:" in stdout


class TestGetGitConfigValue:
    """Tests for get_git_config_value utility function."""

    @pytest.mark.benchmark
    def test_get_git_config_value_success(self, mocker):
        """Test getting a git config value successfully."""
        from commit_check.util import get_git_config_value

        mocker.patch("commit_check.util.cmd_output", return_value="John Doe\n")
        result = get_git_config_value(USER_NAME_CONFIG)
        assert result == "John Doe"

    @pytest.mark.benchmark
    def test_get_git_config_value_not_set(self, mocker):
        """Test getting a git config value when it is not set."""
        from commit_check.util import get_git_config_value

        mocker.patch("commit_check.util.cmd_output", return_value="")
        result = get_git_config_value(USER_NAME_CONFIG)
        assert result == ""

    @pytest.mark.benchmark
    def test_get_git_config_value_exception(self, mocker):
        """Test get_git_config_value returns empty string on CalledProcessError."""
        from commit_check.util import get_git_config_value

        mocker.patch(
            "commit_check.util.cmd_output",
            side_effect=CalledProcessError(
                returncode=1, cmd="git config --get user.name"
            ),
        )
        result = get_git_config_value(USER_NAME_CONFIG)
        assert result == ""

    @pytest.mark.benchmark
    def test_get_git_config_value_email(self, mocker):
        """Test getting user.email from git config."""
        from commit_check.util import get_git_config_value

        mocker.patch("commit_check.util.cmd_output", return_value="alice@example.com\n")
        result = get_git_config_value("user.email")
        assert result == "alice@example.com"


class TestGetTagsAt:
    @staticmethod
    def _git_result(mocker, returncode, stdout):
        return mocker.patch(
            "commit_check.util.subprocess.run",
            return_value=mocker.Mock(returncode=returncode, stdout=stdout, stderr=""),
        )

    @pytest.mark.benchmark
    def test_get_tags_at_lists_tags(self, mocker):
        m_run = self._git_result(mocker, 0, "v1.0.0\nv1.0.1\n")
        retval = get_tags_at()
        assert m_run.call_args[0][0] == ["git", "tag", "--points-at", "HEAD"]
        assert retval == ["v1.0.0", "v1.0.1"]

    @pytest.mark.benchmark
    def test_get_tags_at_passes_rev(self, mocker):
        m_run = self._git_result(mocker, 0, "v2.0.0\n")
        retval = get_tags_at("abc123")
        assert m_run.call_args[0][0] == ["git", "tag", "--points-at", "abc123"]
        assert retval == ["v2.0.0"]

    @pytest.mark.benchmark
    def test_get_tags_at_no_tags(self, mocker, monkeypatch):
        monkeypatch.delenv("GITHUB_REF_TYPE", raising=False)
        self._git_result(mocker, 0, "")
        assert get_tags_at() == []

    @pytest.mark.benchmark
    def test_get_tags_at_git_error_is_not_a_tag(self, mocker, monkeypatch):
        """A git diagnostic on nonzero exit must not be parsed as a tag name."""
        monkeypatch.delenv("GITHUB_REF_TYPE", raising=False)
        mocker.patch(
            "commit_check.util.subprocess.run",
            return_value=mocker.Mock(
                returncode=128,
                stdout="",
                stderr="fatal: bad revision 'HEAD'",
            ),
        )
        assert get_tags_at() == []

    @pytest.mark.benchmark
    def test_get_tags_at_github_actions_tag_fallback(self, mocker, monkeypatch):
        """A tag build's ref name stands in when the local repo has no tag ref."""
        self._git_result(mocker, 0, "")
        monkeypatch.setenv("GITHUB_REF_TYPE", "tag")
        monkeypatch.setenv("GITHUB_REF_NAME", "v3.0.0")
        assert get_tags_at() == ["v3.0.0"]

    @pytest.mark.benchmark
    def test_get_tags_at_env_ignored_for_branch_builds(self, mocker, monkeypatch):
        """A branch build's ref name is not a tag and must not stand in."""
        self._git_result(mocker, 0, "")
        monkeypatch.setenv("GITHUB_REF_TYPE", "branch")
        monkeypatch.setenv("GITHUB_REF_NAME", "main")
        assert get_tags_at() == []

    @pytest.mark.benchmark
    def test_get_tags_at_env_ignored_for_other_rev(self, mocker, monkeypatch):
        """--rev at another commit must not borrow the event's tag name."""
        self._git_result(mocker, 0, "")
        monkeypatch.setenv("GITHUB_REF_TYPE", "tag")
        monkeypatch.setenv("GITHUB_REF_NAME", "v3.0.0")
        monkeypatch.setenv("GITHUB_SHA", "workflowsha")
        assert get_tags_at("othersha") == []

    @pytest.mark.benchmark
    def test_get_tags_at_env_applies_to_workflow_sha(self, mocker, monkeypatch):
        """The workflow's own revision may borrow the event's tag name."""
        self._git_result(mocker, 0, "")
        monkeypatch.setenv("GITHUB_REF_TYPE", "tag")
        monkeypatch.setenv("GITHUB_REF_NAME", "v3.0.0")
        monkeypatch.setenv("GITHUB_SHA", "workflowsha")
        assert get_tags_at("workflowsha") == ["v3.0.0"]

    @pytest.mark.benchmark
    def test_get_tags_at_local_tags_outrank_env(self, mocker, monkeypatch):
        """Real local tags win over the environment fallback."""
        self._git_result(mocker, 0, "v1.0.0\n")
        monkeypatch.setenv("GITHUB_REF_TYPE", "tag")
        monkeypatch.setenv("GITHUB_REF_NAME", "v9.9.9")
        assert get_tags_at() == ["v1.0.0"]


class TestParseSize:
    @pytest.mark.benchmark
    def test_parse_size_accepts_common_forms(self):
        assert parse_size("5MB") == 5 * 1024**2
        assert parse_size("500 KB") == 500 * 1024
        assert parse_size("1gb") == 1024**3
        assert parse_size("12345") == 12345
        assert parse_size("1.5MB") == int(1.5 * 1024**2)
        assert parse_size(4096) == 4096

    @pytest.mark.benchmark
    def test_parse_size_rejects_unusable_values(self):
        """An unusable limit disables the rule rather than failing every file."""
        for bad in ["", "  ", "abc", "MB", None, [], 0, -5, True, 1.5]:
            assert parse_size(bad) is None, bad


class TestFormatSize:
    @pytest.mark.benchmark
    def test_format_size_picks_largest_fitting_unit(self):
        assert format_size(200) == "200 B"
        assert format_size(1536) == "1.5 KB"
        assert format_size(5 * 1024**2) == "5 MB"
        assert format_size(int(2.5 * 1024**3)) == "2.5 GB"


class TestGetCommitFiles:
    @staticmethod
    def _git(tmp_path, *args):
        result = subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    def _repo(self, tmp_path):
        self._git(tmp_path, "init", "-q")
        self._git(tmp_path, "config", "user.name", "T")
        self._git(tmp_path, "config", "user.email", "t@example.com")

    # No benchmark mark: CodSpeed executes marked tests more than once against
    # the same tmp_path, and this test's mkdir/commit sequence only works on a
    # fresh directory.
    def test_lists_touched_files_with_sizes(self, tmp_path, monkeypatch):
        self._repo(tmp_path)
        (tmp_path / "small.txt").write_text("hi")
        sub = tmp_path / "dir"
        sub.mkdir()
        (sub / "bigger.bin").write_bytes(b"x" * 2048)
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-qm", "feat: add files")
        monkeypatch.chdir(tmp_path)
        files = dict(get_commit_files())
        assert files == {"small.txt": 2, "dir/bigger.bin": 2048}

    @pytest.mark.benchmark
    def test_deletions_are_excluded(self, tmp_path, monkeypatch):
        self._repo(tmp_path)
        (tmp_path / "doomed.txt").write_text("x")
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-qm", "feat: add")
        self._git(tmp_path, "rm", "-q", "doomed.txt")
        self._git(tmp_path, "commit", "-qm", "chore: remove")
        monkeypatch.chdir(tmp_path)
        assert get_commit_files() == []

    # No benchmark mark: a second execution has nothing new to commit, so the
    # helper's returncode assertion would fail under CodSpeed's re-runs.
    def test_rev_names_the_commit(self, tmp_path, monkeypatch):
        self._repo(tmp_path)
        (tmp_path / "first.txt").write_text("1")
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-qm", "feat: first")
        first = self._git(tmp_path, "rev-parse", "HEAD")
        (tmp_path / "second.txt").write_text("22")
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-qm", "feat: second")
        monkeypatch.chdir(tmp_path)
        assert dict(get_commit_files(first)) == {"first.txt": 1}
        assert dict(get_commit_files()) == {"second.txt": 2}

    @pytest.mark.benchmark
    def test_unresolvable_rev_is_empty(self, tmp_path, monkeypatch):
        self._repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        assert get_commit_files("doesnotexist") == []

    @pytest.mark.benchmark
    def test_ls_tree_failure_yields_no_files(self, mocker):
        """A failing size lookup reports nothing rather than a partial set."""
        diff = mocker.Mock(returncode=0, stdout="a.txt\0", stderr="")
        tree = mocker.Mock(returncode=128, stdout="", stderr="fatal: bad object")
        mocker.patch("commit_check.util.subprocess.run", side_effect=[diff, tree])
        assert get_commit_files() == []

    @pytest.mark.benchmark
    def test_partial_batch_failure_reports_nothing(self, mocker):
        """One failed batch must not shrink the set the rules then pass on."""
        diff = mocker.Mock(returncode=0, stdout="a.txt\0", stderr="")
        ok = mocker.Mock(
            returncode=0, stdout="100644 blob abc     5\ta.txt\0", stderr=""
        )
        bad = mocker.Mock(returncode=128, stdout="", stderr="fatal")
        mocker.patch("commit_check.util.subprocess.run", side_effect=[diff, ok, bad])
        mocker.patch(
            "commit_check.util._pathspec_batches",
            return_value=[[":(top,literal)a.txt"], [":(top,literal)b.txt"]],
        )
        assert get_commit_files() == []

    @pytest.mark.benchmark
    def test_unrunnable_command_line_reports_nothing(self, mocker):
        """An OSError (Windows arg limits) is not an accidental pass."""
        diff = mocker.Mock(returncode=0, stdout="a.txt\0", stderr="")
        mocker.patch(
            "commit_check.util.subprocess.run",
            side_effect=[diff, OSError("arg list too long")],
        )
        assert get_commit_files() == []

    # No benchmark mark: real-git tests are not safe under CodSpeed re-runs.
    def test_runs_from_a_subdirectory(self, tmp_path, monkeypatch):
        """Paths are repo-relative wherever commit-check is invoked from.

        ls-tree reads pathspecs relative to the cwd, so without an anchored
        pathspec every rule would find no files -- and pass -- in a commit
        that fails at the repository root.
        """
        self._repo(tmp_path)
        sub = tmp_path / "sub" / "deep"
        sub.mkdir(parents=True)
        (sub / "nested.txt").write_bytes(b"x" * 7)
        (tmp_path / "top.txt").write_bytes(b"y" * 5)
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-qm", "feat: add files")

        monkeypatch.chdir(tmp_path)
        from_root = dict(get_commit_files())
        monkeypatch.chdir(sub)
        from_sub = dict(get_commit_files())

        assert from_root == {"sub/deep/nested.txt": 7, "top.txt": 5}
        assert from_sub == from_root

    # No benchmark mark: real-git test, see above.
    def test_merge_commit_reports_what_it_brings_in(self, tmp_path, monkeypatch):
        """A merge is diffed against its first parent, not treated as empty.

        diff-tree prints nothing for a merge by default, which would let a
        prohibited file arrive through a merge unexamined -- exactly the
        commit CI checks on a pull request.
        """
        self._repo(tmp_path)
        (tmp_path / "base.txt").write_text("base")
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-qm", "chore: base")
        self._git(tmp_path, "checkout", "-qb", "feature")
        (tmp_path / "leaked.pem").write_text("KEY")
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-qm", "feat: add key")
        self._git(tmp_path, "checkout", "-q", "-")
        self._git(tmp_path, "merge", "-q", "--no-ff", "feature", "-m", "chore: merge")

        monkeypatch.chdir(tmp_path)
        assert dict(get_commit_files()) == {"leaked.pem": 3}


class TestPathspecBatches:
    @pytest.mark.benchmark
    def test_paths_are_anchored_and_literal(self):
        from commit_check.util import _pathspec_batches

        assert _pathspec_batches(["a[1].txt"]) == [[":(top,literal)a[1].txt"]]

    @pytest.mark.benchmark
    def test_batches_are_capped_by_count(self):
        from commit_check.util import _pathspec_batches

        batches = _pathspec_batches([f"f{i}.txt" for i in range(1200)])
        assert [len(b) for b in batches] == [500, 500, 200]

    @pytest.mark.benchmark
    def test_long_paths_split_before_the_count_cap(self):
        """A few huge paths must not build a command line git cannot run."""
        from commit_check.util import _pathspec_batches, _LS_TREE_ARG_BUDGET

        batches = _pathspec_batches(["x" * 4000 for _ in range(20)])
        assert len(batches) > 1
        assert all(
            sum(len(spec) + 1 for spec in b) <= _LS_TREE_ARG_BUDGET + 4020
            for b in batches
        )


class TestGetPushCommits:
    @staticmethod
    def _git(tmp_path, *args):
        result = subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, encoding="utf-8"
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    # No benchmark mark: real-git test, see above.
    def test_range_covers_every_pushed_commit(self, tmp_path, monkeypatch):
        from commit_check.util import get_push_commits

        self._git(tmp_path, "init", "-q", "-b", "main")
        self._git(tmp_path, "config", "user.name", "T")
        self._git(tmp_path, "config", "user.email", "t@example.com")
        (tmp_path / "base.txt").write_text("base")
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-qm", "chore: base")
        remote = self._git(tmp_path, "rev-parse", "HEAD")
        (tmp_path / "a.txt").write_text("a")
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-qm", "feat: a")
        (tmp_path / "b.txt").write_text("b")
        self._git(tmp_path, "add", "-A")
        self._git(tmp_path, "commit", "-qm", "feat: b")
        local = self._git(tmp_path, "rev-parse", "HEAD")

        monkeypatch.chdir(tmp_path)
        commits = get_push_commits(local, remote)
        assert len(commits) == 2
        assert local in commits
        assert remote not in commits

    @pytest.mark.benchmark
    def test_unresolvable_range_falls_back_to_the_tip(self, mocker):
        """A range this clone cannot compute still leaves the tip worth checking."""
        from commit_check.util import get_push_commits

        mocker.patch(
            "commit_check.util.subprocess.run",
            return_value=mocker.Mock(returncode=128, stdout="", stderr="fatal"),
        )
        assert get_push_commits("deadbeef", "cafebabe") == ["deadbeef"]


class TestParseSizeOverflow:
    @pytest.mark.benchmark
    def test_infinite_sizes_are_unusable(self):
        """inf-like values disable the rule instead of aborting the run."""
        assert parse_size("inf") is None
        assert parse_size("1e999MB") is None
        assert parse_size("nan") is None
