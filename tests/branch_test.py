from commit_check import PASS, FAIL
from commit_check.branch import check_branch, check_merge_base

# used by get_branch_name mock
FAKE_BRANCH_NAME = "fake_branch_name"
LOCATION = "commit_check.branch"


class TestCheckBranch:
    def test_check_branch(self, mocker):
        # Must call get_branch_name, re.match at once.
        checks = [{
            "check": "branch",
            "regex": "dummy_regex"
        }]
        m_get_branch_name = mocker.patch(
            f"{LOCATION}.get_branch_name",
            return_value=FAKE_BRANCH_NAME
        )
        m_re_match = mocker.patch(
            "re.match",
            return_value="fake_rematch_resp"
        )
        retval = check_branch(checks)
        assert retval == PASS
        assert m_get_branch_name.call_count == 1
        assert m_re_match.call_count == 1

    def test_check_branch_with_empty_checks(self, mocker):
        # Must NOT call get_branch_name, re.match with `checks` param with length 0.
        checks = []
        m_get_branch_name = mocker.patch(
            f"{LOCATION}.get_branch_name",
            return_value=FAKE_BRANCH_NAME
        )
        m_re_match = mocker.patch(
            "re.match",
            return_value="fake_branch_name"
        )
        retval = check_branch(checks)
        assert retval == PASS
        assert m_get_branch_name.call_count == 0
        assert m_re_match.call_count == 0

    def test_check_branch_with_different_check(self, mocker):
        # Must NOT call get_branch_name, re.match with not `branch`.
        checks = [{
            "check": "message",
            "regex": "dummy_regex"
        }]
        m_get_branch_name = mocker.patch(
            f"{LOCATION}.get_branch_name",
            return_value=FAKE_BRANCH_NAME
        )
        m_re_match = mocker.patch(
            "re.match",
            return_value="fake_branch_name"
        )
        retval = check_branch(checks)
        assert retval == PASS
        assert m_get_branch_name.call_count == 0
        assert m_re_match.call_count == 0

    def test_check_branch_with_len0_regex(self, mocker, capfd):
        # Must NOT call get_branch_name, re.match with `regex` with length 0.
        checks = [
            {
                "check": "branch",
                "regex": ""
            }
        ]
        m_get_branch_name = mocker.patch(
            f"{LOCATION}.get_branch_name",
            return_value=FAKE_BRANCH_NAME
        )
        m_re_match = mocker.patch(
            "re.match",
            return_value="fake_rematch_resp"
        )
        retval = check_branch(checks)
        assert retval == PASS
        assert m_get_branch_name.call_count == 0
        assert m_re_match.call_count == 0
        out, _ = capfd.readouterr()
        assert "Not found regex for branch naming." in out

    def test_check_branch_with_result_none(self, mocker):
        # Must call print_error_message, print_suggestion when re.match returns NONE.
        checks = [{
            "check": "branch",
            "regex": "dummy_regex",
            "error": "error",
            "suggest": "suggest"
        }]
        m_get_branch_name = mocker.patch(
            f"{LOCATION}.get_branch_name",
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
        retval = check_branch(checks)
        assert retval == FAIL
        assert m_get_branch_name.call_count == 1
        assert m_re_match.call_count == 1
        assert m_print_error_message.call_count == 1
        assert m_print_suggestion.call_count == 1


class TestCheckMergeBase:
    def test_check_merge_base_pass(self, mocker):
        # Must call get_merge_base at once.
        checks = [{
            "check": "merge_base",
            "regex": "main",
            "error": "error",
            "suggest": "suggest",
        }]
        mocker.patch(
            f"{LOCATION}.check_merge_base",
            return_value=0
        )
        retval = check_merge_base(checks)
        assert retval == PASS

    def test_check_merge_base_fail(self, mocker):
        # Must call get_merge_base at once.
        checks = [{
            "check": "merge_base",
            "regex": "abcdefg",
            "error": "error",
            "suggest": "suggest",
        }]
        mocker.patch(
            f"{LOCATION}.check_merge_base",
            return_value=1
        )
        retval = check_merge_base(checks)
        assert retval == FAIL
