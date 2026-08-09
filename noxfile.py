import nox
import glob
import os
import subprocess
import tempfile
from pathlib import Path

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["lint"]

# -----------------------------------------------------------------------------
# Development Commands
# -----------------------------------------------------------------------------


@nox.session()
def lint(session):
    session.install("pre-commit")
    # only need pre-commit hook for local development
    session.run("pre-commit", "install", "--hook-type", "pre-commit")
    session.run("pre-commit", "run", "--all-files")


@nox.session(name="test-hook")
def test_hook(session):
    session.install("-e", ".")
    session.install("pre-commit")
    session.run("pre-commit", "try-repo", ".")


@nox.session()
def build(session):
    session.run("python3", "-m", "pip", "wheel", "--no-deps", "-w", "dist", ".")


@nox.session(name="install", requires=["build"])
def install_wheel(session):
    session.run("python3", "-m", "pip", "wheel", "--no-deps", "-w", "dist", ".")
    whl_file = glob.glob("dist/*.whl")
    session.install(str(whl_file[0]))


def _pull_request_commits():
    """Messages of the commits a pull request adds, or ``[]`` outside one.

    On a ``pull_request`` checkout HEAD is a synthetic merge commit: HEAD^1
    is the base tip and HEAD^2 the branch tip, so HEAD^1..HEAD^2 is the
    pull request. Locally there is no such commit and this returns nothing.
    """
    if subprocess.run(
        ["git", "rev-parse", "-q", "--verify", "HEAD^2"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode:
        return []
    log = subprocess.run(
        ["git", "log", "--pretty=format:%B%x00", "--reverse", "HEAD^1..HEAD^2"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [message for message in log.split("\0") if message.strip()]


@nox.session(name="commit-check")
def commit_check(session):
    """Check this repository with the commit-check in this checkout.

    Not with a released one: a self-test that cannot see the change under
    test is not a self-test. #540 had its own title rejected by the bug it
    was fixing, because CI ran the version before it.

    The commits are enumerated rather than left to ``commit-check
    --message``, which inspects HEAD alone. In CI that is the merge commit,
    which the engine skips -- so the bare form reports a pass having read
    nothing at all.
    """
    session.install(".")
    executable = os.path.join(session.bin, "commit-check")
    failures = []

    def check(label, *args):
        session.log(f"--- {label}")
        # stdin is closed deliberately. Left open, commit-check waits to read
        # a message even for checks that do not take one, and the session
        # hangs instead of failing.
        completed = subprocess.run(
            [executable, *args, "--no-banner"], stdin=subprocess.DEVNULL
        )
        if completed.returncode:
            failures.append(label)

    messages = _pull_request_commits()
    if not messages and os.getenv("GITHUB_EVENT_NAME") == "pull_request":
        session.error(
            "HEAD is not a merge commit, so the pull request's commits "
            "cannot be enumerated. Refusing to report a pass without "
            "checking anything."
        )

    with tempfile.TemporaryDirectory() as directory:
        for index, message in enumerate(messages, start=1):
            path = Path(directory, f"message-{index}")
            path.write_text(message, encoding="utf-8")
            check(f"commit {index}/{len(messages)}", "--message", str(path))

        if not messages:
            # Run from a working copy: HEAD is the thing to check.
            check("HEAD", "--message")

        # Only CI knows the title, and only a squash merge commits it.
        title = os.getenv("PR_TITLE")
        if title:
            path = Path(directory, "pr-title")
            path.write_text(title, encoding="utf-8")
            check("pull request title", "--message", str(path))

    # --branch resolves GITHUB_HEAD_REF when the checkout is detached, so
    # these need no extra context. They report on the configured identity,
    # falling back to HEAD's author -- the same thing the action reports.
    check("branch and author", "--branch", "--author-name", "--author-email")

    if failures:
        session.error(f"commit-check failed: {', '.join(failures)}")


@nox.session()
def coverage(session):
    session.install(".[test]")
    session.run("coverage", "run", "--source", "commit_check", "-m", "pytest")
    session.run("coverage", "report")
    session.run("coverage", "xml")
