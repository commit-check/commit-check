"""Check exclusions"""
# import re
# from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
# from commit_check.util import get_commits_info, print_error_message, print_suggestion


def parser_excludes(excludes: list) -> int:
    for exclude in excludes:
        if exclude['exclude'] == "author_name":
            pass

    return 0
