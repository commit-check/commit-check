import re
from commit_check import YELLOW, RESET_COLOR
from commit_check.util import get_commit_message, error_tips


def check_message(config) -> bool:
    checks = config['checks']
    for check in checks:
        if check['check'] == 'message':
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found regex for commit message. skip checking.{RESET_COLOR}",
                )
                return True
            commit_messages = get_commit_message()
            for commit_message in commit_messages:
                result = re.match(check['regex'], commit_message)
                if result is None:
                    error_tips(
                        check['check'], check['regex'],
                        check['error'], commit_message,
                    )
                    return False
    return True
