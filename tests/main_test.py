import sys
import pytest
from commit_check.main import main
from commit_check import PASS, FAIL, DEFAULT_CONFIG

CMD = "commit-check"


class TestMain:
    def test_commit_invokes_expected_checks(self, mocker):
        """Given a config with several check types, ensure each dispatcher target is invoked exactly once."""
        mocker.patch(
            "commit_check.main.validate_config",
            return_value={
                "checks": [
                    {"check": "message"},
                    {"check": "author_name"},
                    {"check": "author_email"},
                    {"check": "commit_signoff"},
                    {"check": "imperative"},
                ]
            },
        )
        m_msg = mocker.patch("commit_check.commit.check_commit_msg", return_value=PASS)
        m_author = mocker.patch("commit_check.author.check_author", return_value=PASS)
        m_signoff = mocker.patch(
            "commit_check.commit.check_commit_signoff", return_value=PASS
        )
        m_imperative = mocker.patch(
            "commit_check.commit.check_imperative", return_value=PASS
        )
        # Use flags for each check instead of deprecated 'commit' subcommand
        sys.argv = [CMD, "-m", "-n", "-e", "-s", "-i"]
        assert main() == PASS
        assert m_msg.call_count == 1
        # author_name + author_email => 2 invocations
        assert m_author.call_count == 2
        assert m_signoff.call_count == 1
        assert m_imperative.call_count == 1

    def test_help(self, capfd):
        sys.argv = [CMD, "--help"]
        with pytest.raises(SystemExit):
            main()
        out, _ = capfd.readouterr()
        assert "usage:" in out

    def test_version(self):
        # argparse defines --version
        sys.argv = [CMD, "--version"]
        with pytest.raises(SystemExit):
            main()

    def test_default_config_used_when_validate_returns_empty(self, mocker):
        mocker.patch("commit_check.main.validate_config", return_value={})
        m_msg = mocker.patch("commit_check.commit.check_commit_msg", return_value=PASS)

        mocker.patch("commit_check.author.check_author", return_value=PASS)
        mocker.patch("commit_check.commit.check_commit_signoff", return_value=PASS)
        mocker.patch("commit_check.commit.check_imperative", return_value=PASS)
        sys.argv = [CMD, "-m", "-n", "-e", "-s", "-i"]
        main()
        # first positional arg to check_commit_msg is the list of checks
        assert m_msg.call_args[0][0] == DEFAULT_CONFIG["checks"]

    @pytest.mark.parametrize(
        "message_result, author_name_result, author_email_result, signoff_result, imperative_result, expected",
        [
            (PASS, PASS, PASS, PASS, PASS, PASS),
            (FAIL, PASS, PASS, PASS, PASS, FAIL),
            (PASS, FAIL, PASS, PASS, PASS, FAIL),
            (PASS, PASS, FAIL, PASS, PASS, FAIL),
            (PASS, PASS, PASS, FAIL, PASS, FAIL),
            (PASS, PASS, PASS, PASS, FAIL, FAIL),
        ],
    )
    def test_exit_code_aggregation(
        self,
        mocker,
        message_result,
        author_name_result,
        author_email_result,
        signoff_result,
        imperative_result,
        expected,
    ):
        # configure all check types
        mocker.patch(
            "commit_check.main.validate_config",
            return_value={
                "checks": [
                    {"check": "message"},
                    {"check": "author_name"},
                    {"check": "author_email"},
                    {"check": "commit_signoff"},
                    {"check": "imperative"},
                ]
            },
        )

        mocker.patch(
            "commit_check.commit.check_commit_msg", return_value=message_result
        )

        def author_side_effect(_, which, **_kw):  # type: ignore[return]
            return author_name_result if which == "author_name" else author_email_result

        mocker.patch("commit_check.author.check_author", side_effect=author_side_effect)
        mocker.patch(
            "commit_check.commit.check_commit_signoff", return_value=signoff_result
        )
        mocker.patch(
            "commit_check.commit.check_imperative", return_value=imperative_result
        )
        sys.argv = [CMD, "-m", "-n", "-e", "-s", "-i"]
        assert main() == expected

    def test_unknown_check_type_ignored(self, mocker):
        mocker.patch(
            "commit_check.main.validate_config",
            return_value={"checks": [{"check": "totally_unknown"}]},
        )
        # no dispatcher functions patched intentionally
        # No flags: unknown check type should simply be ignored, resulting in PASS (no executed checks)
        sys.argv = [CMD]
        assert main() == PASS
