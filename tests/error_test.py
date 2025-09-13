import os
import pytest
from commit_check.error import error_handler, log_and_exit


@pytest.mark.benchmark
def test_error_handler_RuntimeError():
    with pytest.raises(SystemExit) as exit_info:
        with error_handler():
            raise RuntimeError("Test error")
    assert exit_info.value.code == 1


@pytest.mark.benchmark
def test_error_handler_KeyboardInterrupt():
    with pytest.raises(SystemExit) as exit_info:
        with error_handler():
            raise KeyboardInterrupt
    assert exit_info.value.code == 130


@pytest.mark.benchmark
def test_error_handler_unexpected_error():
    with pytest.raises(SystemExit) as exit_info:
        with error_handler():
            raise Exception("Test error")
    assert exit_info.value.code == 3


@pytest.mark.benchmark
def test_error_handler_cannot_access(mocker):
    with pytest.raises(SystemExit):
        store_dir = "/fake/commit-check"
        log_path = os.path.join(store_dir, "commit-check.log")
        mocker.patch.dict(os.environ, {"COMMIT_CHECK_HOME": store_dir})
        mock_os_access = mocker.patch("os.access", return_value=False)
        mocker.patch("os.path.exists", return_value=True)
        mocker.patch("os.makedirs")
        mock_open = mocker.patch("builtins.open", mocker.mock_open())
        mocker.patch("commit_check.util.cmd_output", return_value="mock_version")
        mocker.patch("sys.version", "Mock Python Version")
        mocker.patch("sys.executable", "/mock/path/to/python")

        from commit_check.error import log_and_exit

        log_and_exit(
            msg="Test error message",
            ret_code=1,
            exc=ValueError("Test exception"),
            formatted="Mocked formatted stack trace",
        )

        mock_os_access.assert_called_once_with(store_dir, os.W_OK)
        mock_open.assert_called_with(log_path, "a")
        mock_open().write.assert_any_call(f"Failed to write to log at {log_path}\n")


@pytest.mark.benchmark
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
