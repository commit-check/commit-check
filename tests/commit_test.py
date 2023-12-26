from commit_check import PASS, FAIL
from commit_check.commit import check_commit_msg, get_default_commit_msg_file, read_commit_msg, check_commit_signoff

# used by get_commits_info mock
FAKE_BRANCH_NAME = "fake_commits_info"
# The location of check_commit_msg()
LOCATION = "commit_check.commit"
# Commit message file
MSG_FILE = '.git/COMMIT_EDITMSG'


def test_get_default_commit_msg_file(mocker):
    retval = get_default_commit_msg_file()
    assert retval == ".git/COMMIT_EDITMSG"


def test_read_commit_msg_from_existing_file(tmp_path):
    # Create a temporary file with a known content
    commit_msg_content = "Test commit message content."
    commit_msg_file = tmp_path / "test_commit_msg.txt"
    commit_msg_file.write_text(commit_msg_content)

    result = read_commit_msg(commit_msg_file)
    assert result == commit_msg_content


def test_read_commit_msg_file_not_found(mocker):
    m_commits_info = mocker.patch('commit_check.util.get_commits_info', return_value='mocked_commits_info')
    read_commit_msg("non_existent_file.txt")
    assert m_commits_info.call_count == 0


def test_check_commit_with_empty_checks(mocker):
    checks = []
    m_re_match = mocker.patch(
        "re.match",
        return_value="fake_commits_info"
    )
    retval = check_commit_msg(checks, MSG_FILE)
    assert retval == PASS
    assert m_re_match.call_count == 0


def test_check_commit_with_different_check(mocker):
    checks = [{
        "check": "branch",
        "regex": "dummy_regex"
    }]
    m_re_match = mocker.patch(
        "re.match",
        return_value="fake_commits_info"
    )
    retval = check_commit_msg(checks, MSG_FILE)
    assert retval == PASS
    assert m_re_match.call_count == 0


def test_check_commit_with_len0_regex(mocker, capfd):
    checks = [
        {
            "check": "message",
            "regex": ""
        }
    ]
    m_re_match = mocker.patch(
        "re.match",
        return_value="fake_rematch_resp"
    )
    retval = check_commit_msg(checks, MSG_FILE)
    assert retval == PASS
    assert m_re_match.call_count == 0
    out, _ = capfd.readouterr()
    assert "Not found regex for commit message." in out


def test_check_commit_with_result_none(mocker):
    checks = [{
        "check": "message",
        "regex": "dummy_regex",
        "error": "error",
        "suggest": "suggest"
    }]
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
    assert m_re_match.call_count == 1
    assert m_print_error_message.call_count == 1
    assert m_print_suggestion.call_count == 1


def test_check_commit_signoff(mocker):
    checks = [{
        "check": "commit_signoff",
        "regex": "dummy_regex",
        "error": "error",
        "suggest": "suggest"
    }]
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
    retval = check_commit_signoff(checks)
    assert retval == FAIL
    assert m_re_match.call_count == 1
    assert m_print_error_message.call_count == 1
    assert m_print_suggestion.call_count == 1


def test_check_commit_signoff_with_empty_regex(mocker):
    checks = [{
        "check": "commit_signoff",
        "regex": "",
        "error": "error",
        "suggest": "suggest"
    }]
    m_re_match = mocker.patch(
        "re.match",
        return_value="fake_commits_info"
    )
    retval = check_commit_signoff(checks)
    assert retval == PASS
    assert m_re_match.call_count == 0


def test_check_commit_signoff_with_empty_checks(mocker):
    checks = []
    m_re_match = mocker.patch(
        "re.match",
        return_value="fake_commits_info"
    )
    retval = check_commit_signoff(checks)
    assert retval == PASS
    assert m_re_match.call_count == 0
