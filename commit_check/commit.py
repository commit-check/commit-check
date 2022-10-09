import re
from commit_check import YELLOW, RESET_COLOR
from commit_check.util import get_commit_message, get_committer_email, print_error_message


def check_commit_message(config) -> bool:
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
                    print_error_message(
                        check['check'], check['regex'],
                        check['error'], commit_message,
                    )
                    return False
    return True


def check_committer_email(config) -> bool:
    checks = config['checks']
    for check in checks:
        if check['check'] == 'email':
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found regex for committer email. skip checking.{RESET_COLOR}",
                )
                return True
            committer_emails = get_committer_email()
            for committer_email in committer_emails:
                result = re.match(check['regex'], committer_email)
                if result is None:
                    print_error_message(
                        check['check'], check['regex'],
                        check['error'], committer_email,
                    )
                    return False
    return True
