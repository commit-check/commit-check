from commit_check import PASS, FAIL
from commit_check.commit import check_commit_msg

# used by get_commits_info mock
FAKE_BRANCH_NAME = "fake_commits_info"
# The location of check_commit_msg()
LOCATION = "commit_check.commit"
# Commit message file
MSG_FILE = '.git/COMMIT_EDITMSG'


class TestCommit:
    def test_check_commit_with_empty_checks(self, mocker):
        # Must NOT call get_commits_info, re.match. with `checks` param with length 0.
        checks = []
        m_get_commits_info = mocker.patch(
            f"{LOCATION}.get_commits_info",
            return_value=FAKE_BRANCH_NAME
        )
        m_re_match = mocker.patch(
            "re.match",
            return_value="fake_commits_info"
        )
        retval = check_commit_msg(checks, MSG_FILE)
        assert retval == PASS
        assert m_get_commits_info.call_count == 0
        assert m_re_match.call_count == 0

    def test_check_commit_with_different_check(self, mocker):
        # Must NOT call get_commit_info, re.match with not `message`.
        checks = [{
            "check": "branch",
            "regex": "dummy_regex"
        }]
        m_get_commits_info = mocker.patch(
            f"{LOCATION}.get_commits_info",
            return_value=FAKE_BRANCH_NAME
        )
        m_re_match = mocker.patch(
            "re.match",
            return_value="fake_commits_info"
        )
        retval = check_commit_msg(checks, MSG_FILE)
        assert retval == PASS
        assert m_get_commits_info.call_count == 0
        assert m_re_match.call_count == 0

    def test_check_commit_with_len0_regex(self, mocker, capfd):
        # Must NOT call get_commits_info, re.match with `regex` with length 0.
        checks = [
            {
                "check": "message",
                "regex": ""
            }
        ]
        m_get_commits_info = mocker.patch(
            f"{LOCATION}.get_commits_info",
            return_value=FAKE_BRANCH_NAME
        )
        m_re_match = mocker.patch(
            "re.match",
            return_value="fake_rematch_resp"
        )
        retval = check_commit_msg(checks, MSG_FILE)
        assert retval == PASS
        assert m_get_commits_info.call_count == 0
        assert m_re_match.call_count == 0
        out, _ = capfd.readouterr()
        assert "Not found regex for commit message." in out

    def test_check_commit_with_result_none(self, mocker):
        # Must call print_error_message, print_suggestion when re.match returns NONE.
        checks = [{
            "check": "message",
            "regex": "dummy_regex",
            "error": "error",
            "suggest": "suggest"
        }]
        m_get_commits_info = mocker.patch(
            f"{LOCATION}.get_commits_info",
            return_value=FAKE_BRANCH_NAME
        )
        m_re_match = mocker.patch(
            "re.match",
            return_value=None
        )
        m_print_error_message = mocker.patch(
            f"{LOCATION}.print_error_message"
        )
        m_print_suggestion = mocker.patch(
            f"{LOCATION}.print_suggestion"
        )
        retval = check_commit_msg(checks, MSG_FILE)
        assert retval == FAIL
        assert m_get_commits_info.call_count == 1
        assert m_re_match.call_count == 1
        assert m_print_error_message.call_count == 1
        assert m_print_suggestion.call_count == 1
