import sys
import pytest
import tempfile
import os
from commit_check.main import main

CMD = "commit-check"


class TestMain:
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

    def test_no_args_shows_help(self, capfd):
        """When no arguments are provided, should show help and exit 0."""
        sys.argv = [CMD]
        assert main() == 0

    def test_message_validation_with_valid_commit(self, mocker):
        """Test that a valid commit message passes validation."""
        # Mock stdin to provide a valid commit message
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="feat: add new feature\n")

        sys.argv = [CMD, "-m"]
        assert main() == 0

    def test_message_validation_with_invalid_commit(self, mocker):
        """Test that an invalid commit message fails validation."""
        # Mock stdin to provide an invalid commit message
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="invalid commit message\n")

        sys.argv = [CMD, "-m"]
        assert main() == 1

    def test_message_validation_from_file(self):
        """Test validation of commit message from a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("fix: resolve bug")
            f.flush()

            try:
                sys.argv = [CMD, "-m", f.name]
                assert main() == 0
            finally:
                os.unlink(f.name)

    def test_branch_validation(self, mocker):
        """Test branch name validation."""
        # Mock git command to return a valid branch name
        mocker.patch(
            "subprocess.run",
            return_value=type(
                "MockResult", (), {"stdout": "feature/test-branch", "returncode": 0}
            )(),
        )

        sys.argv = [CMD, "-b"]
        assert main() == 0

    def test_author_name_validation(self, mocker):
        """Test author name validation."""
        # Mock git command to return a valid author name
        mocker.patch(
            "subprocess.run",
            return_value=type(
                "MockResult", (), {"stdout": "John Doe", "returncode": 0}
            )(),
        )

        sys.argv = [CMD, "-n"]
        assert main() == 0

    def test_author_email_validation(self, mocker):
        """Test author email validation."""
        # Mock git command to return a valid author email
        mocker.patch(
            "subprocess.run",
            return_value=type(
                "MockResult", (), {"stdout": "john.doe@example.com", "returncode": 0}
            )(),
        )

        sys.argv = [CMD, "-e"]
        assert main() == 0

    def test_dry_run_always_passes(self, mocker):
        """Test that dry run mode always returns 0."""
        # Mock stdin to provide an invalid commit message
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value="invalid commit message\n")

        sys.argv = [CMD, "-m", "--dry-run"]
        assert main() == 0
