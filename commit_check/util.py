"""
``commit_check.util``
---------------------

A module containing utility functions.
"""

import subprocess
from pathlib import Path, PurePath
from subprocess import CalledProcessError
import yaml
from commit_check import RED, GREEN, YELLOW, RESET_COLOR
from commit_check.rules import build_checks_from_toml
from typing import Any, Dict, List, Optional

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
        if check.get('check') == check_type:
            return check
    return None


def _print_failure(
    check: dict,
    regex: str,
    actual: str
) -> None:
    """Print a standardized failure message."""
    if not print_error_header.has_been_called:
        print_error_header()
    print_error_message(check['check'], regex, check.get('error', ''), actual)
    if check.get('suggest'):
        print_suggestion(check.get('suggest'))


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
        commands = ['git', 'branch', '--show-current']
        branch_name = cmd_output(commands) or "HEAD"
    except CalledProcessError:
        branch_name = ''
    return branch_name.strip()


def has_commits() -> bool:
    """Check if there are any commits in the current branch.
    :returns: `True` if there are commits, `False` otherwise.
    """
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
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
            'git', 'log', '-n', '1', f"--pretty=format:%{format_string}", f"{sha}",
        ]
        output = cmd_output(commands)
    except CalledProcessError:
        output = ''
    return output


def git_merge_base(target_branch: str, current_branch: str) -> int:
    """Check ancestors for a given commit.
    :param target_branch: target branch
    :param current_branch: default is HEAD

    :returns: 0 if ancestor exists, 1 if not, 128 if git command fails.
    """
    try:
        commands = ['git', 'merge-base', '--is-ancestor', f'{target_branch}', f'{current_branch}']
        result = subprocess.run(
            commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8'
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
        commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8'
    )
    if result.returncode == 0 and result.stdout is not None:
        return result.stdout
    elif result.stderr != '':
        return result.stderr
    else:
        return ''


def _load_toml(path: PurePath) -> Dict[str, Any]:
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


def _find_config_file(path_hint: str) -> Optional[PurePath]:
    """Resolve config file.

    - If a directory is passed, search in priority: commit-check.toml, cchk.toml
    - If a file ending with .toml is passed, use it if exists.
    - Ignore legacy .commit-check.yml entirely.
    """
    p = Path(path_hint)
    if p.is_dir():
        for name in ("commit-check.toml", "cchk.toml"):
            candidate = p / name
            if candidate.exists():
                return candidate
        return None
    # If explicit file path provided
    if str(p).endswith((".toml",)) and p.exists():
        return p
    return None


def _build_checks_from_toml(conf: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Translate high-level TOML options into internal checks list."""
    checks: List[Dict[str, Any]] = []

    commit_cfg = conf.get("commit", {}) or {}
    branch_cfg = conf.get("branch", {}) or {}
    author_cfg = conf.get("author", {}) or {}

    # message regex (Conventional Commits)
    if commit_cfg.get("conventional_commits", True):
        checks.append({
            "check": "message",
            "regex": r"^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)|(Merge).*|(fixup!.*)",
            "error": "The commit message should follow Conventional Commits. See https://www.conventionalcommits.org",
            "suggest": "Use <type>(<scope>): <description> with allowed types",
        })

    # Imperative mood check
    if commit_cfg.get("subject_imperative", True):
        checks.append({
            "check": "imperative",
            "regex": "",
            "error": "Commit message should use imperative mood (e.g., 'Add feature' not 'Added feature')",
            "suggest": "Use imperative mood in the subject line",
        })

    # Branch naming
    if branch_cfg.get("conventional_branch", True):
        allowed = branch_cfg.get("allow_branch_types") or [
            "bugfix", "feature", "release", "hotfix", "task", "chore", "feat", "fix",
        ]
        allowed_re = "|".join(sorted(set(allowed)))
        regex = rf"^({allowed_re})\/.+|(master)|(main)|(HEAD)|(PR-.+)"
        checks.append({
            "check": "branch",
            "regex": regex,
            "error": "Branches must begin with allowed types (e.g., feature/, bugfix/) or be main/master/PR-*.",
            "suggest": "git checkout -b <type>/<branch_name>",
        })

    # Merge base requirement
    target = branch_cfg.get("require_rebase_target")
    if isinstance(target, str) and target:
        checks.append({
            "check": "merge_base",
            "regex": target,
            "error": "Current branch is not rebased onto target branch",
            "suggest": "Rebase or merge with the target branch",
        })

    # Author checks (basic format validation retained)
    checks.append({
        "check": "author_name",
        "regex": r"^[A-Za-zÀ-ÖØ-öø-ÿ\u0100-\u017F\u0180-\u024F ,.'\-]+$|.*(\[bot])",
        "error": "The committer name seems invalid",
        "suggest": "git config user.name 'Your Name'",
    })
    checks.append({
        "check": "author_email",
        "regex": r"^.+@.+$",
        "error": "The committer's email seems invalid",
        "suggest": "git config user.email yourname@example.com",
    })

    # Signoff requirement
    if author_cfg.get("require_signed_off_by", False):
        checks.append({
            "check": "commit_signoff",
            "regex": r"Signed-off-by:.*[A-Za-z0-9]\s+<.+@.+>",
            "error": "Signed-off-by not found in latest commit",
            "suggest": "git commit --amend --signoff or use --signoff on commit",
        })

    return {"checks": checks}


def validate_config(path_hint: str) -> dict:
    """Validate and load configuration from TOML.

    Returns a dict containing a 'checks' list or empty dict if not found/invalid.
    """
    cfg_path = _find_config_file(path_hint)
    if cfg_path:
        raw = _load_toml(cfg_path)
        if not raw:
            return {}
        return build_checks_from_toml(raw)

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


def print_error_message(check_type: str, regex: str, error: str, reason: str):
    """Print error message.
    :param check_type:
    :param regex:
    :param error:
    :param reason:

    :returns: Give error messages to user
    """
    print(f"Type {YELLOW}{check_type}{RESET_COLOR} check failed => {RED}{reason}{RESET_COLOR} ", end='',)
    print("")
    print(f"It doesn't match regex: {regex}")
    print(error)


def print_suggestion(suggest: str | None) -> None:
    """Print suggestion to user
    :param suggest: what message to print out
    """
    if suggest:
        print(
            f"Suggest: {GREEN}{suggest}{RESET_COLOR} ", end='',
        )
    else:
        print(f"commit-check does not support {suggest} yet.")
        raise SystemExit(1)
    print('\n')
