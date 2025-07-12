import pytest
from commit_check import PASS, FAIL
from commit_check.commit import check_commit_msg, get_default_commit_msg_file, read_commit_msg, check_commit_signoff, check_imperative

# used by get_commit_info mock
FAKE_BRANCH_NAME = "fake_commits_info"
# The location of check_commit_msg()
LOCATION = "commit_check.commit"
# Commit message file
MSG_FILE = '.git/COMMIT_EDITMSG'


@pytest.mark.benchmark
def test_get_default_commit_msg_file(mocker):
    retval = get_default_commit_msg_file()
    assert retval == ".git/COMMIT_EDITMSG"


@pytest.mark.benchmark
def test_read_commit_msg_from_existing_file(tmp_path):
    # Create a temporary file with a known content
    commit_msg_content = "Test commit message content."
    commit_msg_file = tmp_path / "test_commit_msg.txt"
    commit_msg_file.write_text(commit_msg_content)

    result = read_commit_msg(commit_msg_file)
    assert result == commit_msg_content


@pytest.mark.benchmark
def test_read_commit_msg_file_not_found(mocker):
    m_commits_info = mocker.patch('commit_check.util.get_commit_info', return_value='mocked_commits_info')
    read_commit_msg("non_existent_file.txt")
    assert m_commits_info.call_count == 0


@pytest.mark.benchmark
def test_check_commit_msg_no_commit_msg_file(mocker):
    mock_get_default_commit_msg_file = mocker.patch(
        "commit_check.commit.get_default_commit_msg_file",
        return_value=".git/COMMIT_EDITMSG"
    )
    mock_read_commit_msg = mocker.patch(
        "commit_check.commit.read_commit_msg",
        return_value="Sample commit message"
    )

    checks = [{"regex": ".*", "check": "message", "error": "Invalid", "suggest": None}]

    result = check_commit_msg(checks, commit_msg_file="")

    mock_get_default_commit_msg_file.assert_called_once()
    mock_read_commit_msg.assert_called_once_with(".git/COMMIT_EDITMSG")
    assert result == 0


@pytest.mark.benchmark
def test_check_commit_with_empty_checks(mocker):
    checks = []
    m_re_match = mocker.patch(
        "re.match",
        return_value="fake_commits_info"
    )
    retval = check_commit_msg(checks, MSG_FILE)
    assert retval == PASS
    assert m_re_match.call_count == 0


@pytest.mark.benchmark
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


@pytest.mark.benchmark
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


@pytest.mark.benchmark
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


@pytest.mark.benchmark
def test_check_commit_signoff(mocker):
    checks = [{
        "check": "commit_signoff",
        "regex": "dummy_regex",
        "error": "error",
        "suggest": "suggest"
    }]
    m_re_search = mocker.patch(
        "re.search",
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
    assert m_re_search.call_count == 1
    assert m_print_error_message.call_count == 1
    assert m_print_suggestion.call_count == 1


@pytest.mark.benchmark
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


@pytest.mark.benchmark
def test_check_commit_signoff_with_empty_checks(mocker):
    checks = []
    m_re_match = mocker.patch(
        "re.match",
        return_value="fake_commits_info"
    )
    retval = check_commit_signoff(checks)
    assert retval == PASS
    assert m_re_match.call_count == 0


@pytest.mark.benchmark
def test_check_imperative_pass(mocker):
    """Test imperative mood check passes for valid imperative mood."""
    checks = [{
        "check": "imperative",
        "regex": "",
        "error": "Commit message should use imperative mood",
        "suggest": "Use imperative mood"
    }]

    mocker.patch(
        "commit_check.commit.read_commit_msg",
        return_value="feat: Add new feature\n\nThis adds a new feature to the application."
    )

    retval = check_imperative(checks, MSG_FILE)
    assert retval == PASS


@pytest.mark.benchmark
def test_check_imperative_fail_past_tense(mocker):
    """Test imperative mood check fails for past tense."""
    checks = [{
        "check": "imperative",
        "regex": "",
        "error": "Commit message should use imperative mood",
        "suggest": "Use imperative mood"
    }]

    mocker.patch(
        "commit_check.commit.read_commit_msg",
        return_value="feat: Added new feature"
    )

    m_print_error_message = mocker.patch(
        f"{LOCATION}.print_error_message"
    )
    m_print_suggestion = mocker.patch(
        f"{LOCATION}.print_suggestion"
    )

    retval = check_imperative(checks, MSG_FILE)
    assert retval == FAIL
    assert m_print_error_message.call_count == 1
    assert m_print_suggestion.call_count == 1


@pytest.mark.benchmark
def test_check_imperative_fail_present_continuous(mocker):
    """Test imperative mood check fails for present continuous."""
    checks = [{
        "check": "imperative",
        "regex": "",
        "error": "Commit message should use imperative mood",
        "suggest": "Use imperative mood"
    }]

    mocker.patch(
        "commit_check.commit.read_commit_msg",
        return_value="feat: Adding new feature"
    )

    m_print_error_message = mocker.patch(
        f"{LOCATION}.print_error_message"
    )
    m_print_suggestion = mocker.patch(
        f"{LOCATION}.print_suggestion"
    )

    retval = check_imperative(checks, MSG_FILE)
    assert retval == FAIL
    assert m_print_error_message.call_count == 1
    assert m_print_suggestion.call_count == 1


@pytest.mark.benchmark
def test_check_imperative_skip_merge_commit(mocker):
    """Test imperative mood check skips merge commits."""
    checks = [{
        "check": "imperative",
        "regex": "",
        "error": "Commit message should use imperative mood",
        "suggest": "Use imperative mood"
    }]

    mocker.patch(
        "commit_check.commit.read_commit_msg",
        return_value="Merge branch 'feature/test' into main"
    )

    retval = check_imperative(checks, MSG_FILE)
    assert retval == PASS


@pytest.mark.benchmark
def test_check_imperative_different_check_type(mocker):
    """Test imperative mood check skips different check types."""
    checks = [{
        "check": "message",
        "regex": "dummy_regex"
    }]

    m_read_commit_msg = mocker.patch(
        "commit_check.commit.read_commit_msg",
        return_value="feat: Added new feature"
    )

    retval = check_imperative(checks, MSG_FILE)
    assert retval == PASS
    assert m_read_commit_msg.call_count == 0


@pytest.mark.benchmark
def test_check_imperative_no_commits(mocker):
    """Test imperative mood check passes when there are no commits."""
    checks = [{
        "check": "imperative",
        "regex": "",
        "error": "Commit message should use imperative mood",
        "suggest": "Use imperative mood"
    }]

    mocker.patch("commit_check.commit.has_commits", return_value=False)

    retval = check_imperative(checks, MSG_FILE)
    assert retval == PASS


@pytest.mark.benchmark
def test_check_imperative_empty_checks(mocker):
    """Test imperative mood check with empty checks list."""
    checks = []

    m_read_commit_msg = mocker.patch(
        "commit_check.commit.read_commit_msg",
        return_value="feat: Added new feature"
    )

    retval = check_imperative(checks, MSG_FILE)
    assert retval == PASS
    assert m_read_commit_msg.call_count == 0


@pytest.mark.benchmark
def test_is_imperative_valid_cases():
    """Test _is_imperative function with valid imperative mood cases."""
    from commit_check.commit import _is_imperative

    valid_cases = [
        "Add new feature",
        "Fix bug in authentication",
        "Update documentation",
        "Remove deprecated code",
        "Refactor user service",
        "Optimize database queries",
        "Create new component",
        "Delete unused files",
        "Improve error handling",
        "Enhance user experience",
        "Implement new API",
        "Configure CI/CD pipeline",
        "Setup testing framework",
        "Handle edge cases",
        "Process user input",
        "Validate form data",
        "Transform data format",
        "Initialize application",
        "Load configuration",
        "Save user preferences",
        "",  # Empty description should pass
    ]

    for case in valid_cases:
        assert _is_imperative(case), f"'{case}' should be imperative mood"


@pytest.mark.benchmark
def test_is_imperative_invalid_cases():
    """Test _is_imperative function with invalid imperative mood cases."""
    from commit_check.commit import _is_imperative

    invalid_cases = [
        "Added new feature",
        "Fixed bug in authentication",
        "Updated documentation",
        "Removed deprecated code",
        "Refactored user service",
        "Optimized database queries",
        "Created new component",
        "Deleted unused files",
        "Improved error handling",
        "Enhanced user experience",
        "Implemented new API",
        "Adding new feature",
        "Fixing bug in authentication",
        "Updating documentation",
        "Removing deprecated code",
        "Refactoring user service",
        "Optimizing database queries",
        "Creating new component",
        "Deleting unused files",
        "Improving error handling",
        "Enhancing user experience",
        "Implementing new API",
        "Adds new feature",
        "Fixes bug in authentication",
        "Updates documentation",
        "Removes deprecated code",
        "Refactors user service",
        "Optimizes database queries",
        "Creates new component",
        "Deletes unused files",
        "Improves error handling",
        "Enhances user experience",
        "Implements new API",
    ]

    for case in invalid_cases:
        assert not _is_imperative(case), f"'{case}' should not be imperative mood"
