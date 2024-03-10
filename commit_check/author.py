"""Check git author name and email"""
import re
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import get_commit_info, print_error_message, print_suggestion


def check_author(checks: list, check_type: str) -> int:
    for check in checks:
        if check['check'] == check_type:
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found regex for {check_type}. skip checking.{RESET_COLOR}",
                )
                return PASS
            if check_type == "author_name":
                format_str = "an"
            if check_type == 'author_email':
                format_str = "ae"
            config_value = str(get_commit_info(format_str))
            result = re.match(check['regex'], config_value)
            if result is None:
                print_error_message(
                    check['check'], check['regex'],
                    check['error'], config_value,
                )
                if check['suggest']:
                    print_suggestion(check['suggest'])
                return FAIL
    return PASS
