"""Check git branch naming convention."""
import re
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import get_branch_name, git_merge_base, print_error_header, print_error_message, print_suggestion


def check_branch(checks: list) -> int:
    for check in checks:
        if check['check'] == 'branch':
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found regex for branch naming. skip checking.{RESET_COLOR}",
                )
                return PASS
            branch_name = get_branch_name()
            result = re.match(check['regex'], branch_name)
            if result is None:
                if not print_error_header.has_been_called:
                    print_error_header()
                print_error_message(
                    check['check'], check['regex'],
                    check['error'], branch_name,
                )
                if check['suggest']:
                    print_suggestion(check['suggest'])
                return FAIL
    return PASS


def check_merge_base(checks: list) -> int:
    """Check if the current branch is based on the latest target branch.
    params checks: List of check configurations containing merge_base rules

    :returns PASS(0) if merge base check succeeds, FAIL(1) otherwise
    """
    for check in checks:
        if check['check'] == 'merge_base':
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found target branch for checking merge base. skip checking.{RESET_COLOR}",
                )
                return PASS
            result = git_merge_base(check['regex'], 'HEAD')
            if result != 0:
                branch_name = get_branch_name()
                if not print_error_header.has_been_called:
                    print_error_header()
                print_error_message(
                    check['check'], check['regex'],
                    check['error'], branch_name,
                )
                if check.get('suggest'):
                    print_suggestion(f"Run 'git rebase {check['regex']}' to update your branch")
                return FAIL
    return PASS
