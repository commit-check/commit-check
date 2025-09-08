"""Check git branch naming convention."""
import re
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import _find_check, get_branch_name, git_merge_base, print_error_header, print_error_message, print_suggestion, has_commits


def _print_failure(check: dict, regex: str, actual: str) -> None:
    if not print_error_header.has_been_called:
        print_error_header()  # pragma: no cover
    print_error_message(check['check'], regex, check['error'], actual)
    if check.get('suggest'):
        print_suggestion(check['suggest'])


def check_branch(checks: list) -> int:
    check = _find_check(checks, 'branch')
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

    _print_failure(check, regex, branch_name)
    return FAIL


def check_merge_base(checks: list) -> int:
    """Check if the current branch is based on the latest target branch.
    params checks: List of check configurations containing merge_base rules

    :returns PASS(0) if merge base check succeeds, FAIL(1) otherwise
    """
    if has_commits() is False:
        return PASS # pragma: no cover

    # locate merge_base rule, if any
    check = _find_check(checks, 'merge_base')
    if not check:
        return PASS

    regex = check.get('regex', "")
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

    _print_failure(check, regex, current_branch)
    return FAIL
