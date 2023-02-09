import os
import pytest
from commit_check.error import error_handler, log_and_exit


def test_error_handler_RuntimeError():
    with pytest.raises(SystemExit) as exit_info:
        with error_handler():
            raise RuntimeError("Test error")
    assert exit_info.value.code == 1


def test_error_handler_KeyboardInterrupt():
    with pytest.raises(SystemExit) as exit_info:
        with error_handler():
            raise KeyboardInterrupt
    assert exit_info.value.code == 130


def test_error_handler_unexpected_error():
    with pytest.raises(SystemExit) as exit_info:
        with error_handler():
            raise Exception("Test error")
    assert exit_info.value.code == 3


@pytest.mark.xfail
def test_log_and_exit(monkeypatch):
    monkeypatch.setenv("COMMIT_CHECK_HOME", "")
    monkeypatch.setenv("XDG_CACHE_HOME", "")

    error_msg = "Test error message"
    ret_code = 123
    exc = Exception("Test error")
    formatted = "Test formatted traceback"

    log_and_exit(error_msg, ret_code, exc, formatted)

    log_path = os.path.expanduser("~/.cache/commit-check/commit-check.log")
    with open(log_path) as file:
        log_content = file.read()

    assert error_msg in log_content
    assert str(ret_code) in log_content
    assert str(exc) in log_content
    assert formatted in log_content
