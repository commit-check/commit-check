from commit_check import PASS, FAIL
from commit_check.commit import check_commit_msg, get_default_commit_msg_file, read_commit_msg

# used by get_commits_info mock
FAKE_BRANCH_NAME = "fake_commits_info"
# The location of check_commit_msg()
LOCATION = "commit_check.commit"
# Commit message file
MSG_FILE = '.git/COMMIT_EDITMSG'


def test_get_default_commit_msg_file(mocker):
    mocker.patch("commit_check.util.cmd_output", return_value="git_dir_output")
    retval = get_default_commit_msg_file()
    assert retval == ".git/COMMIT_EDITMSG"


def test_read_commit_msg_file_found(tmp_path):
    # Create a temporary file with content
    commit_msg_file = tmp_path / "commit_msg.txt"
    content = "Test commit message"
    commit_msg_file.write_text(content)

    result = read_commit_msg(commit_msg_file)
    assert result == content


def test_read_commit_msg_file_not_found(mocker):
    mocker.patch(f'{LOCATION}.get_commits_info', return_value="Last commit message")
    result = read_commit_msg("nonexistent_file.txt")
    assert result == "Last commit message"


def test_check_commit_with_empty_checks(mocker):
    # Must NOT call get_commits_info, re.match. with `checks` param with length 0.
    checks = []
    m_re_match = mocker.patch(
        "re.match",
        return_value="fake_commits_info"
    )
    retval = check_commit_msg(checks, MSG_FILE)
    assert retval == PASS
    assert m_re_match.call_count == 0


def test_check_commit_with_different_check(mocker):
    # Must NOT call get_commit_info, re.match with not `message`.
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
    # Must NOT call get_commits_info, re.match with `regex` with length 0.
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
    # Must call print_error_message, print_suggestion when re.match returns NONE.
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
