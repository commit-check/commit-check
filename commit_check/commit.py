import re
from commit_check import YELLOW, RESET_COLOR
from commit_check.util import get_commits_info, print_error_message


def check_commits(config, check_type) -> bool:
    checks = config['checks']
    for check in checks:
        if check['check'] == check_type:
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found regex for {check_type}. skip checking.{RESET_COLOR}",
                )
                return True
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
                    return False
    return True

# def check_commit_message(config) -> bool:
#     checks = config['checks']
#     for check in checks:
#         if check['check'] == 'commit_message':
#             if check['regex'] == "":
#                 print(
#                     f"{YELLOW}Not found regex for commit message. skip checking.{RESET_COLOR}",
#                 )
#                 return True
#             commit_messages = get_commit_message()
#             for commit_message in commit_messages:
#                 result = re.match(check['regex'], commit_message)
#                 if result is None:
#                     print_error_message(
#                         check['check'], check['regex'],
#                         check['error'], commit_message,
#                     )
#                     return False
#     return True


# def check_committer_email(config) -> bool:
#     checks = config['checks']
#     for check in checks:
#         if check['check'] == 'author_email':
#             if check['regex'] == "":
#                 print(
#                     f"{YELLOW}Not found regex for committer email. skip checking.{RESET_COLOR}",
#                 )
#                 return True
#             committer_emails = get_committer_info("ae")
#             for committer_email in committer_emails:
#                 result = re.match(check['regex'], committer_email)
#                 if result is None:
#                     print_error_message(
#                         check['check'], check['regex'],
#                         check['error'], committer_email,
#                     )
#                     return False
#     return True


# def check_committer_name(config) -> bool:
#     checks = config['checks']
#     for check in checks:
#         if check['check'] == 'author_email':
#             if check['regex'] == "":
#                 print(
#                     f"{YELLOW}Not found regex for committer email. skip checking.{RESET_COLOR}",
#                 )
#                 return True
#             committer_names = get_committer_info("an")
#             for committer_name in committer_names:
#                 result = re.match(check['regex'], committer_name)
#                 if result is None:
#                     print_error_message(
#                         check['check'], check['regex'],
#                         check['error'], committer_name,
#                     )
#                     return False
#     return True
