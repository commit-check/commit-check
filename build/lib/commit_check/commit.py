import re
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import get_commits_info, print_error_message


def check_commits(config, check_type) -> int:
    checks = config['checks']
    for check in checks:
        if check['check'] == check_type:
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found regex for {check_type}. skip checking.{RESET_COLOR}",
                )
                return PASS
            format_string = ""
            if check_type == "commit_message":
                format_string = "s"
            elif check_type == "author_name":
                format_string = "an"
            elif check_type == "author_email":
                format_string = "ae"
            commits_info = get_commits_info(format_string)
            for commit_info in commits_info:
                result = re.match(check['regex'], commit_info)
                if result is None:
                    print_error_message(
                        check['check'], check['regex'],
                        check['error'], commit_info,
                    )
                    return FAIL
    return PASS
