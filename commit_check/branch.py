"""Check git branch naming convention."""
import re
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import get_branch_name, git_merge_base, print_error_header, print_error_message, print_suggestion, has_commits


def _find_branch_check(checks: list) -> dict | None:
    """Return the first branch check config or None if not present."""
    for check in checks:
        if check.get('check') == 'branch':
            return check
    return None


def check_branch(checks: list) -> int:
    check = _find_branch_check(checks)
    if not check:
        return PASS

    regex = check.get('regex', "")
    if regex == "":
        print(
            f"{YELLOW}Not found regex for branch naming. skip checking.{RESET_COLOR}",
        )
        return PASS

    branch_name = get_branch_name()
    if re.match(regex, branch_name):
        return PASS

    if not print_error_header.has_been_called:
        print_error_header()  # pragma: no cover
    print_error_message(
        check['check'], regex,
        check['error'], branch_name,
    )
    if check.get('suggest'):
        print_suggestion(check['suggest'])
    return FAIL


def check_merge_base(checks: list) -> int:
    """Check if the current branch is based on the latest target branch.
    params checks: List of check configurations containing merge_base rules

    :returns PASS(0) if merge base check succeeds, FAIL(1) otherwise
    """
    if has_commits() is False:
        return PASS # pragma: no cover

    # locate merge_base rule, if any
    merge_check = next((c for c in checks if c.get('check') == 'merge_base'), None)
    if not merge_check:
        return PASS

    regex = merge_check.get('regex', "")
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

    if not print_error_header.has_been_called:
        print_error_header() # pragma: no cover
    print_error_message(
        merge_check['check'], regex,
        merge_check['error'], current_branch,
    )
    if merge_check.get('suggest'):
        print_suggestion(merge_check['suggest'])
    return FAIL
