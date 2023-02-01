"""Check git commit message formatting"""
import re
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import get_commits_info, print_error_message, print_suggestion


def check_commit(checks: list) -> int:
    for check in checks:
        if check['check'] == 'message':
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found regex for commit message. skip checking.{RESET_COLOR}",
                )
                return PASS
            message = str(get_commits_info("s"))
            result = re.match(check['regex'], message)
            if result is None:
                print_error_message(
                    check['check'], check['regex'],
                    check['error'], message,
                )
                if check['suggest']:
                    print_suggestion(check['suggest'])
                return FAIL
    return PASS
