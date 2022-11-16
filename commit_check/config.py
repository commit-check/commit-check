"""Check git configuration"""
import re
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import get_config, print_error_message, print_suggestion


def check_config(config, check_type) -> int:
    checks = config['checks']
    for check in checks:
        if check['check'] == check_type:
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found regex for {check_type}. skip checking.{RESET_COLOR}",
                )
                return PASS
            if check_type == "author_name":
                config_name = "user.name"
            if check_type == 'author_email':
                config_name = "user.email"
            config_value = get_config(config_name)
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
