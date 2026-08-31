"""
``commit_check.util``
---------------------

A module containing utility functions.
"""

from __future__ import annotations
import os
import subprocess
import sys
from subprocess import CalledProcessError
from commit_check import RED, GREEN, YELLOW, RESET_COLOR
from commit_check.rules_catalog import display_name


def _print_failure(
    check: dict,
    actual: str,
    no_banner: bool = False,
    compact: bool = False,
) -> None:
    """Print a standardized failure message."""
    rule_id = check.get("rule_id", "")
    if compact:
        compact_value = actual.splitlines()[0] if actual else actual
        name = display_name(check["check"])
        label = f"{rule_id} {name}" if rule_id else name
        print(f"[FAIL] {label}: {compact_value}")
        return
    if not no_banner and not print_error_header.has_been_called:
        print_error_header()
    docs_url = check.get("docs_url", "") or ""
    print_error_message(
        check["check"],
        check.get("error", ""),
        actual,
        rule_id=rule_id,
        docs_url=docs_url,
    )
    if check.get("suggest"):
        print_suggestion(check["suggest"])
    # When the ID above is already a link, repeating the URL only adds a line
    # to read. Without hyperlink support — a pipe, a CI log — it is the only
    # way the reader gets the address at all, so it stays.
    if docs_url and not (rule_id and supports_hyperlinks()):
        print(f"Docs: {docs_url}")
    # Blank line closes the whole block, rather than splitting it before the
    # documentation link.
    print()


def get_branch_name() -> str:
    """Identify current branch name.
    .. note::
        With Git 2.22 and above supports `git branch --show-current`
        Please open an issue at https://github.com/commit-check/commit-check/issues
        if you encounter any issue.

    :returns: A `str` describing the current branch name.
    """
    try:
        # Git 2.22 and above supports `git branch --show-current`
        commands = ["git", "branch", "--show-current"]
        branch_name = cmd_output(commands)
    except CalledProcessError:
        branch_name = ""

    if not branch_name:
        # Fallback to environment variables (GitHub Actions)
        branch_name = (
            os.getenv("GITHUB_HEAD_REF") or os.getenv("GITHUB_REF_NAME") or "HEAD"
        )
    return branch_name.strip()


def get_tags_at(rev: str = "HEAD") -> list[str]:
    """List the tags pointing at a revision.

    :param rev: Revision whose tags to list, ``HEAD`` by default.
    :returns: Tag names pointing at the revision, oldest first. When the
        repository has none there but the run is a GitHub Actions tag build
        (``GITHUB_REF_TYPE=tag``) checking that build's own revision, the
        pushed tag name from ``GITHUB_REF_NAME`` stands in — a shallow or
        partial checkout may not carry the tag ref even though the workflow
        was triggered by it.
    """
    # Run git directly: cmd_output() returns stderr text on a nonzero exit,
    # and a git diagnostic must not be parsed as a tag name.
    result = subprocess.run(
        ["git", "tag", "--points-at", rev],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    output = result.stdout if result.returncode == 0 else ""

    tags = [line.strip() for line in output.splitlines() if line.strip()]
    if (
        not tags
        and os.getenv("GITHUB_REF_TYPE") == "tag"
        # Only the workflow's own revision may borrow the event's tag name:
        # with --rev at another commit the pushed tag says nothing about it.
        and rev in ("HEAD", os.getenv("GITHUB_SHA"))
    ):
        ref_name = os.getenv("GITHUB_REF_NAME", "").strip()
        if ref_name:
            tags = [ref_name]
    return tags


_SIZE_UNITS = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}


def parse_size(value) -> int | None:
    """Parse a human file size into bytes.

    Accepts an ``int`` (bytes) or a string with an optional binary unit
    suffix — ``"5MB"``, ``"500 KB"``, ``"1gb"``, ``"12345"`` — where
    ``KB``/``MB``/``GB`` are powers of 1024.

    :param value: The configured size.
    :returns: The size in bytes, or ``None`` when the value is empty,
        non-positive, or not a size at all — an unusable limit disables the
        rule rather than failing every file.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if not isinstance(value, str):
        return None

    text = value.strip().upper().replace(" ", "")
    if not text:
        return None
    for suffix, factor in sorted(_SIZE_UNITS.items(), key=lambda kv: -len(kv[0])):
        if text.endswith(suffix):
            number = text[: -len(suffix)]
            break
    else:
        number, factor = text, 1
    try:
        size = int(float(number) * factor)
    except (ValueError, OverflowError):
        return None
    return size if size > 0 else None


def format_size(size: int) -> str:
    """Render a byte count with the largest fitting binary unit."""
    for suffix in ("GB", "MB", "KB"):
        factor = _SIZE_UNITS[suffix]
        if size >= factor:
            value = size / factor
            text = f"{value:.1f}".rstrip("0").rstrip(".")
            return f"{text} {suffix}"
    return f"{size} B"


def get_commit_files(rev: str = "HEAD") -> list[tuple[str, int]]:
    """List the files a commit touches, with their sizes at that commit.

    Deletions are excluded — removing a file adds nothing to police — and so
    are non-blob entries such as submodules. Sizes are the blob sizes as of
    the commit, not whatever the working tree holds now.

    :param rev: Revision whose changed files to list, ``HEAD`` by default.
    :returns: ``(path, size_in_bytes)`` pairs, empty when the revision does
        not resolve or touches nothing.
    """
    diff = subprocess.run(
        [
            "git",
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "--root",
            "--diff-filter=d",
            "-r",
            "-z",
            rev,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    if diff.returncode != 0:
        return []
    paths = [p for p in diff.stdout.split("\0") if p]
    if not paths:
        return []

    files: list[tuple[str, int]] = []
    # Batch the paths: a commit can touch more files than one command line
    # holds.
    for start in range(0, len(paths), 500):
        # :(literal) keeps a path containing glob characters a path, not a
        # pathspec pattern.
        batch = [f":(literal){p}" for p in paths[start : start + 500]]
        tree = subprocess.run(
            ["git", "ls-tree", "-r", "-l", "-z", rev, "--", *batch],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
        if tree.returncode != 0:
            continue
        for entry in tree.stdout.split("\0"):
            if "\t" not in entry:
                continue
            header, path = entry.split("\t", 1)
            fields = header.split()
            # <mode> <type> <sha> <size>; size is "-" for non-blob entries.
            if len(fields) == 4 and fields[1] == "blob" and fields[3].isdigit():
                files.append((path, int(fields[3])))
    return files


def get_upstream_branch() -> str:
    """Return the configured upstream ref for the current branch.

    :returns: The upstream tracking ref (e.g. ``origin/main``), or "" if none
        is configured.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    if result.returncode == 0 and result.stdout:
        return result.stdout.strip()
    return ""


def get_upstream_remote_sha(upstream_ref: str) -> str:
    """Return the current remote SHA for an upstream ref when available.

    :param upstream_ref: An upstream tracking ref (e.g. ``origin/main``).
    :returns: The 40-character remote SHA, or "" if not available.
    """
    parts = upstream_ref.split("/", 1)
    if len(parts) != 2:
        return ""

    remote_name, branch_name = parts
    return get_remote_branch_sha(remote_name, branch_name)


def get_remote_branch_sha(remote_name: str, branch_name: str) -> str:
    """Return the current remote SHA for a branch when available.

    :param remote_name: Git remote name, e.g. ``origin``.
    :param branch_name: Branch name on the remote, e.g. ``main``.
    :returns: The 40-character remote SHA, or "" if not available.
    """
    if not remote_name or not branch_name:
        return ""

    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", remote_name, f"refs/heads/{branch_name}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    if result.returncode != 0 or not result.stdout:
        return ""

    return result.stdout.split()[0].strip()


def fetch_upstream_ref(upstream_ref: str) -> bool:
    """Fetch an upstream branch so its tip commit is available locally.

    :param upstream_ref: An upstream tracking ref (e.g. ``origin/main``).
    :returns: ``True`` if the fetch succeeded, ``False`` otherwise.
    """
    parts = upstream_ref.split("/", 1)
    if len(parts) != 2:
        return False

    remote_name, branch_name = parts
    result = subprocess.run(
        ["git", "fetch", "--quiet", "--no-tags", remote_name, branch_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    return result.returncode == 0


def get_git_remotes() -> list[str]:
    """Return configured git remote names."""
    result = subprocess.run(
        ["git", "remote"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    if result.returncode != 0 or not result.stdout:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def fetch_remote_ref(remote_name: str, remote_ref: str) -> bool:
    """Fetch a remote ref so its objects are available locally.

    :param remote_name: The git remote name, e.g. ``origin``.
    :param remote_ref: The full ref name, e.g. ``refs/heads/main``.
    :returns: ``True`` if the fetch succeeded, ``False`` otherwise.
    """
    if not remote_name or not remote_ref:
        return False

    result = subprocess.run(
        ["git", "fetch", "--quiet", "--no-tags", remote_name, remote_ref],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    return result.returncode == 0


def has_commits() -> bool:
    """Check if there are any commits in the current branch.
    :returns: `True` if there are commits, `False` otherwise.
    """
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def git_rev_parse_verify(rev: str) -> bool:
    """Check whether a revision resolves in the current repository.
    :param rev: any revision expression, e.g. ``HEAD^2``

    :returns: `True` if the revision resolves, `False` otherwise.
    """
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def get_commit_info(format_string: str, sha: str = "HEAD") -> str:
    """Get latest commits information
    :param format_string: could be
        - s  - subject
        - an - author name
        - ae - author email
        - b  - body
        - H  - commit hash
    more: https://git-scm.com/docs/pretty-formats

    :returns: A `str`.
    """
    try:
        commands = [
            "git",
            "log",
            "-n",
            "1",
            f"--pretty=format:%{format_string}",
            f"{sha}",
        ]
        output = cmd_output(commands)
    except CalledProcessError:
        output = ""
    return output


def get_git_config_value(key: str) -> str:
    """Get a value from git config.
    :param key: git config key, e.g., 'user.name' or 'user.email'
    :returns: The configured value as a `str`, or empty string if not set.
    """
    try:
        commands = ["git", "config", "--get", key]
        output = cmd_output(commands)
        return output.strip()
    except CalledProcessError:
        return ""


def git_merge_base(target_branch: str, current_branch: str) -> int:
    """Check ancestors for a given commit.
    :param target_branch: target branch
    :param current_branch: default is HEAD

    :returns: 0 if ancestor exists, 1 if not, 128 if git command fails.
    """
    try:
        commands = [
            "git",
            "merge-base",
            "--is-ancestor",
            f"{target_branch}",
            f"{current_branch}",
        ]
        result = subprocess.run(
            commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
        )
        return result.returncode
    except CalledProcessError:
        return 128


def cmd_output(commands: list) -> str:
    """Run command
    :param commands: list of commands

    :returns: Get `str` output.
    """
    result = subprocess.run(
        commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
    )
    if result.returncode == 0 and result.stdout is not None:
        return result.stdout
    elif result.stderr != "":
        return result.stderr
    else:
        return ""


def track_print_call(func):
    def wrapper(*args, **kwargs):
        wrapper.has_been_called = True
        return func(*args, **kwargs)

    wrapper.has_been_called = False  # Initialize as False
    return wrapper


@track_print_call
def print_error_header():
    """Print error message.
    :returns: Print error head to user
    """
    print("Commit rejected by Commit-Check.                                  ")
    print("                                                                  ")
    print(r"  (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)  ")
    print(r"   / ._. \      / ._. \      / ._. \      / ._. \      / ._. \   ")
    print(r" __\( C )/__  __\( H )/__  __\( E )/__  __\( C )/__  __\( K )/__ ")
    print(r"(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)")
    print(r"   || E ||      || R ||      || R ||      || O ||      || R ||   ")
    print(r" _.' '-' '._  _.' '-' '._  _.' '-' '._  _.' '-' '._  _.' '-' '._ ")
    print(r"(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)")
    print(r" `-´     `-´  `-´     `-´  `-´     `-´  `-´     `-´  `-´     `-´ ")
    print("                                                                  ")
    print("Commit rejected.                                                  ")
    print("                                                                  ")


#: Terminals known to render OSC 8 hyperlinks, by ``TERM_PROGRAM``.
_HYPERLINK_TERM_PROGRAMS = frozenset(
    {"iTerm.app", "WezTerm", "vscode", "Hyper", "ghostty", "rio"}
)


def supports_hyperlinks() -> bool:
    """Whether the terminal renders OSC 8 hyperlinks.

    A terminal that does not understand the escape sequence may print its
    payload as visible junk, so this errs towards saying no. The signals are
    the ones the wider tooling ecosystem settled on, which is why a link that
    works in ``ruff`` works here too.

    Piped or redirected output always says no: the sequence would end up in
    the file, and a CI log is read as plain text.

    ``FORCE_HYPERLINK`` overrides the detection in both directions, following
    the convention ``FORCE_COLOR`` established: ``0`` turns links off even on a
    terminal that renders them, any other value turns them on.
    """
    forced = os.environ.get("FORCE_HYPERLINK")
    if forced:
        return forced != "0"
    if not sys.stdout.isatty():
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    if os.environ.get("TERM_PROGRAM") in _HYPERLINK_TERM_PROGRAMS:
        return True
    if "kitty" in os.environ.get("TERM", ""):
        return True
    # GNOME Terminal and the other VTE-based terminals, from 0.50 onwards.
    try:
        return int(os.environ.get("VTE_VERSION", "0")) >= 5000
    except ValueError:
        return False


def hyperlink(text: str, url: str) -> str:
    """Wrap ``text`` in an OSC 8 hyperlink pointing at ``url``."""
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def print_error_message(
    check_type: str,
    error: str,
    reason: str,
    rule_id: str = "",
    docs_url: str = "",
) -> None:
    """Print error message.

    :param check_type: the check that failed, e.g. ``subject_imperative``
    :param error: the human-readable explanation of the failure
    :param reason: the offending value
    :param rule_id: stable rule ID, e.g. ``CC003`` (omitted when empty)
    :param docs_url: the rule's documentation, linked from the ID when the
        terminal supports it

    :returns: Give error messages to user
    """
    name = display_name(check_type)
    label = rule_id
    if rule_id and docs_url and supports_hyperlinks():
        label = hyperlink(rule_id, docs_url)
    prefix = f"{YELLOW}{label}{RESET_COLOR} " if rule_id else ""
    print(
        f"{prefix}{YELLOW}{name}{RESET_COLOR} check failed ==> {RED}{reason}{RESET_COLOR}"
    )
    if error:
        print(error)


def print_suggestion(suggest: str) -> None:
    """Print suggestion to user
    :param suggest: what message to print out
    """
    if suggest:
        print(f"Suggest: {GREEN}{suggest}{RESET_COLOR}")
