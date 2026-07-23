"""Integration tests that operate on real (ephemeral) Git repositories.

These tests create temporary Git repositories, make real commits, and run
commit-check against them — complementing the mock-based unit tests by
catching regressions in git-interaction code paths.
"""

from __future__ import annotations
import sys
import pytest
import subprocess
from pathlib import Path
from commit_check.main import main


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command inside *cwd* and return the result."""
    return subprocess.run(
        ("git", *args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _init_repo(tmp: Path) -> None:
    """Initialise a minimal Git repository at *tmp* with a first commit."""
    _git("init", "--initial-branch=main", cwd=tmp)
    _git("config", "user.name", "Test User", cwd=tmp)
    _git("config", "user.email", "test@example.com", cwd=tmp)
    (tmp / "README.md").write_text("# test")
    _git("add", ".", cwd=tmp)
    _git("commit", "-m", "chore: initial commit", cwd=tmp)


# ---------------------------------------------------------------------------
# Fixture: run inside the temp repo
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a fresh Git repo in *tmp_path* and chdir into it."""
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestIntegration:
    """Integration tests using a real (ephemeral) Git repository."""

    # ── message validation ──────────────────────────────────────────────

    @pytest.mark.benchmark
    def test_message_valid_conventional_commit(self, repo: Path):
        """A valid conventional commit message passes --message."""
        _git("commit", "--allow-empty", "-m", "feat: add new endpoint", cwd=repo)

        sys.argv = ["commit-check", "--message"]
        assert main() == 0

    @pytest.mark.benchmark
    def test_message_invalid_commit_fails(self, repo: Path):
        """A commit that does not follow Conventional Commits fails."""
        _git("config", "user.name", "Dev User", cwd=repo)
        _git("commit", "--allow-empty", "-m", "bad commit message", cwd=repo)

        sys.argv = ["commit-check", "--message"]
        assert main() == 1

    @pytest.mark.benchmark
    def test_message_with_custom_config(self, repo: Path):
        """cchk.toml in the repo root is picked up automatically."""
        (repo / "cchk.toml").write_text("[commit]\nsubject_imperative = false\n")
        _git("config", "user.name", "Dev User", cwd=repo)
        _git(
            "commit",
            "--allow-empty",
            "-m",
            "feat: added the feature",
            cwd=repo,
        )
        # 'added' is not imperative, but cchk.toml disabled that check
        sys.argv = ["commit-check", "--message"]
        assert main() == 0

    # ── branch validation ───────────────────────────────────────────────

    @pytest.mark.benchmark
    def test_branch_valid_conventional_branch(self, repo: Path):
        """A branch named feature/xxx passes --branch."""
        _git("checkout", "-b", "feature/add-streaming", cwd=repo)

        sys.argv = ["commit-check", "--branch"]
        assert main() == 0

    @pytest.mark.benchmark
    def test_branch_invalid_branch_fails(self, repo: Path):
        """An unconventionally-named branch fails --branch."""
        _git("checkout", "-b", "wrong-branch-name", cwd=repo)

        sys.argv = ["commit-check", "--branch"]
        assert main() == 1

    # ── author validation ───────────────────────────────────────────────

    @pytest.mark.benchmark
    def test_author_name_configured(self, repo: Path):
        """--author-name passes when user.name is set."""
        _git("config", "user.name", "Alice Smith", cwd=repo)
        sys.argv = ["commit-check", "--author-name"]
        assert main() == 0

    @pytest.mark.benchmark
    def test_author_email_configured(self, repo: Path):
        """--author-email passes when user.email is set."""
        _git("config", "user.email", "alice@example.com", cwd=repo)
        sys.argv = ["commit-check", "--author-email"]
        assert main() == 0

    # ── combined checks ─────────────────────────────────────────────────

    @pytest.mark.benchmark
    def test_full_validation_all_pass(self, repo: Path):
        """message + branch + author all pass on a well-configured repo."""
        _git("checkout", "-b", "feature/add-streaming", cwd=repo)
        _git("config", "user.name", "Alice Smith", cwd=repo)
        _git("config", "user.email", "alice@example.com", cwd=repo)
        _git(
            "commit",
            "--allow-empty",
            "-m",
            "feat: add streaming support",
            cwd=repo,
        )

        sys.argv = [
            "commit-check",
            "--message",
            "--branch",
            "--author-name",
            "--author-email",
        ]
        assert main() == 0

    @pytest.mark.benchmark
    def test_full_validation_message_fails(self, repo: Path):
        """Only the message fails; other checks still report individually."""
        _git("checkout", "-b", "feature/add-streaming", cwd=repo)
        _git("config", "user.name", "Alice Smith", cwd=repo)
        _git("config", "user.email", "alice@example.com", cwd=repo)
        _git("commit", "--allow-empty", "-m", "bad message", cwd=repo)

        sys.argv = [
            "commit-check",
            "--message",
            "--branch",
            "--author-name",
            "--author-email",
        ]
        assert main() == 1

    # ── signoff validation ──────────────────────────────────────────────

    @pytest.mark.benchmark
    def test_signoff_required_passes(self, repo: Path):
        """A commit with Signed-off-by trailer passes."""
        (repo / "cchk.toml").write_text("[commit]\nrequire_signed_off_by = true\n")
        _git(
            "commit",
            "--allow-empty",
            "-m",
            "feat: add feature\n\nSigned-off-by: Test User <test@example.com>",
            cwd=repo,
        )

        sys.argv = ["commit-check", "--message"]
        assert main() == 0

    @pytest.mark.benchmark
    def test_signoff_required_fails(self, repo: Path):
        """A commit without Signed-off-by trailer fails."""
        (repo / "cchk.toml").write_text("[commit]\nrequire_signed_off_by = true\n")
        _git("commit", "--allow-empty", "-m", "feat: add feature", cwd=repo)

        sys.argv = ["commit-check", "--message"]
        assert main() == 1

    # ── dry-run ─────────────────────────────────────────────────────────

    @pytest.mark.benchmark
    def test_dry_run_always_passes(self, repo: Path):
        """--dry-run forces exit code 0 even for invalid input."""
        _git("commit", "--allow-empty", "-m", "bad message", cwd=repo)
        sys.argv = ["commit-check", "--message", "--dry-run"]
        assert main() == 0

    # ── json format ─────────────────────────────────────────────────────

    @pytest.mark.benchmark
    def test_json_format_valid(self, repo: Path):
        """--format json produces parsable output on a valid commit."""
        _git("commit", "--allow-empty", "-m", "feat: add json support", cwd=repo)

        sys.argv = ["commit-check", "--message", "--format", "json"]
        assert main() == 0
