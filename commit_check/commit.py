"""Check git commit message formatting"""
import re
import os
from pathlib import PurePath
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import cmd_output, get_commits_info, print_error_message, print_suggestion


def check_commit_msg(checks: list) -> int:
    for check in checks:
        if check['check'] == 'message':
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found regex for commit message. skip checking.{RESET_COLOR}",
                )
                return PASS
            if os.environ.get("COMMIT_CHECK") == "1":
                dot_git_dir = cmd_output(['git', 'rev-parse', '--git-dir']).strip()
                commit_msg_file = PurePath(dot_git_dir, "COMMIT_EDITMSG")
                with open(commit_msg_file, 'r') as f:
                    commit_msg = f.read()
            else:
                commit_msg = str(get_commits_info("s"))
            result = re.match(check['regex'], commit_msg)
            if result is None:
                print_error_message(
                    check['check'], check['regex'],
                    check['error'], commit_msg,
                )
                if check['suggest']:
                    print_suggestion(check['suggest'])
                return FAIL
    return PASS
