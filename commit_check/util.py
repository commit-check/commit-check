"""
``commit_check.util``
---------------------

A module containing utility functions.
"""

from __future__ import annotations
import os
import subprocess
import yaml
from pathlib import Path, PurePath
from typing import Any
from subprocess import CalledProcessError
from commit_check import RED, GREEN, YELLOW, RESET_COLOR
from commit_check.rule_builder import RuleBuilder

# Prefer stdlib tomllib (3.11+); fall back to tomli if available; else disabled
try:  # pragma: no cover - import paths differ by Python version
    import tomllib as _toml  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    try:
        import tomli as _toml  # type: ignore[no-redef]
    except Exception:  # pragma: no cover
        _toml = None  # type: ignore[assignment]


def _find_check(checks: list, check_type: str) -> dict | None:
    """Return the first check dict matching check_type, else None."""
    for check in checks:
        if check.get("check") == check_type:
            return check
    return None


def _print_failure(
    check: dict,
    actual: str,
    no_banner: bool = False,
    compact: bool = False,
) -> None:
    """Print a standardized failure message."""
    if compact:
        compact_value = actual.splitlines()[0] if actual else actual
        print(f"[FAIL] {check['check']}: {compact_value}")
        return
    if not no_banner and not print_error_header.has_been_called:
        print_error_header()
    print_error_message(check["check"], check.get("error", ""), actual)
    if check.get("suggest"):
        print_suggestion(check.get("suggest"))


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


def _load_toml(path: PurePath) -> dict[str, Any]:
    """Load TOML from file, tolerant if toml support missing."""
    if _toml is None:
        return {}
    try:
        with open(path, "rb") as f:
            return _toml.load(f)  # type: ignore[call-arg]
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def _find_config_file(path_hint: str) -> PurePath | None:
    """Resolve config file.

    - If a directory is passed, search in priority: cchk.toml, commit-check.toml, .github/cchk.toml, .github/commit-check.toml
    - If a file ending with .toml is passed, use it if exists.
    - Ignore legacy .commit-check.yml entirely.
    """
    p = Path(path_hint)
    if p.is_dir():
        for name in (
            "cchk.toml",
            "commit-check.toml",
            ".github/cchk.toml",
            ".github/commit-check.toml",
        ):
            candidate = p / name
            if candidate.exists():
                return candidate
        return None
    # If explicit file path provided
    if str(p).endswith((".toml",)) and p.exists():
        return p
    return None


def validate_config(path_hint: str) -> dict[str, Any]:
    """Validate and load configuration from TOML.

    Returns a dict containing a 'checks' list or empty dict if not found/invalid.
    """
    cfg_path = _find_config_file(path_hint)
    if cfg_path:
        raw = _load_toml(cfg_path)
        if not raw:
            return {}
        # Use new rule builder system
        rule_builder = RuleBuilder(raw)
        rules = rule_builder.build_all_rules()
        return {"checks": [rule.to_dict() for rule in rules]}

    # Legacy YAML fallback (maintained for test compatibility)
    try:
        with open(PurePath(path_hint)) as f:
            data = yaml.safe_load(f)  # type: ignore[no-redef]
            return data or {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


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


def print_error_message(check_type: str, error: str, reason: str):
    """Print error message.
    :param check_type:
    :param error:
    :param reason:

    :returns: Give error messages to user
    """
    print(
        f"Type {YELLOW}{check_type}{RESET_COLOR} check failed ==> {RED}{reason}{RESET_COLOR} ",
        end="",
    )
    print("")
    if error:
        print(error)


def print_suggestion(suggest: str | None) -> None:
    """Print suggestion to user
    :param suggest: what message to print out
    """
    if suggest:
        print(
            f"Suggest: {GREEN}{suggest}{RESET_COLOR} ",
            end="",
        )
    else:
        print(f"commit-check does not support {suggest} yet.")
        raise SystemExit(1)
    print("\n")
