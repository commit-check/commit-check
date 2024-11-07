"""Check git branch naming convention."""
import re
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import get_branch_name, git_merge_base, print_error_message, print_suggestion


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
                print_error_message(
                    check['check'], check['regex'],
                    check['error'], branch_name,
                )
                if check['suggest']:
                    print_suggestion(check['suggest'])
                return FAIL
    return PASS


def check_merge_base(checks: list) -> int:
    for check in checks:
        if check['check'] == 'merge_base':
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found target branch for checking merge base. skip checking.{RESET_COLOR}",
                )
                return PASS
            result = git_merge_base(check['regex'], 'HEAD')
            if result == 1:
                return FAIL
    return PASS
