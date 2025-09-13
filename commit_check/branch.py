"""Check git branch naming convention."""

import re
from typing import Optional
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import (
    _find_check,
    _print_failure,
    get_branch_name,
    git_merge_base,
    has_commits,
)


def check_branch(checks: list, stdin_text: Optional[str] = None) -> int:
    check = _find_check(checks, "branch")
    if not check:
        return PASS

    regex = check.get("regex", "")
    if regex == "":
        print(
            f"{YELLOW}Not found regex for branch naming. skip checking.{RESET_COLOR}",
        )
        return PASS

    branch_name = stdin_text.strip() if stdin_text is not None else get_branch_name()
    if re.match(regex, branch_name):
        return PASS

    _print_failure(check, regex, branch_name)
    return FAIL


def check_merge_base(checks: list) -> int:
    """Check if the current branch is based on the latest target branch.
    params checks: List of check configurations containing merge_base rules

    :returns PASS(0) if merge base check succeeds, FAIL(1) otherwise
    """
    if has_commits() is False:
        return PASS  # pragma: no cover

    # locate merge_base rule, if any
    check = _find_check(checks, "merge_base")
    if not check:
        return PASS

    regex = check.get("regex", "")
    if regex == "":
        print(
            f"{YELLOW}Not found target branch for checking merge base. skip checking.{RESET_COLOR}",
        )
        return PASS

    target_branch = regex if "origin/" in regex else f"origin/{regex}"
    current_branch = get_branch_name()
    result = git_merge_base(target_branch, current_branch)
    if result == 0:
        return PASS
    # Treat missing target (128) as skip only when detached HEAD (cannot verify ancestry reliably)
    if result == 128 and current_branch == "HEAD":
        return PASS

    _print_failure(check, regex, current_branch)
    return FAIL


# --- Additional per-option checks (aliases to existing ones) ---


def check_conventional_branch(checks: list, stdin_text: Optional[str] = None) -> int:
    """Alias to check_branch for explicit rule mapping."""
    return check_branch(checks, stdin_text=stdin_text)


def check_require_rebase_target(checks: list) -> int:
    """Alias to check_merge_base for explicit rule mapping."""
    return check_merge_base(checks)
