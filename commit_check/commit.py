"""Check git commit message formatting"""
import re
from pathlib import PurePath
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import cmd_output, get_commit_info, print_error_message, print_suggestion


def get_default_commit_msg_file() -> str:
    """Get the default commit message file."""
    git_dir = cmd_output(['git', 'rev-parse', '--git-dir']).strip()
    return str(PurePath(git_dir, "COMMIT_EDITMSG"))


def read_commit_msg(commit_msg_file) -> str:
    """Read the commit message from the specified file."""
    try:
        with open(commit_msg_file, 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Commit message is composed by subject and body
        return str(get_commit_info("s") + "\n\n" + get_commit_info("b"))


def check_commit_msg(checks: list, commit_msg_file: str = "") -> int:
    if commit_msg_file is None or commit_msg_file == "":
        commit_msg_file = get_default_commit_msg_file()

    commit_msg = read_commit_msg(commit_msg_file)

    for check in checks:
        if check['regex'] == "":
            print(
                f"{YELLOW}Not found regex for commit message. skip checking.{RESET_COLOR}",
            )
            return PASS

        if check['check'] == 'message':
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


def check_commit_signoff(checks: list, commit_msg_file: str = "") -> int:
    if commit_msg_file is None or commit_msg_file == "":
        commit_msg_file = get_default_commit_msg_file()

    for check in checks:
        if check['check'] == 'commit_signoff':
            if check['regex'] == "":
                print(
                    f"{YELLOW}Not found regex for commit signoff. skip checking.{RESET_COLOR}",
                )
                return PASS

            commit_msg = read_commit_msg(commit_msg_file)
            commit_hash = get_commit_info("H")
            result = re.search(check['regex'], commit_msg)
            if result is None:
                print_error_message(
                    check['check'], check['regex'],
                    check['error'], commit_hash,
                )
                if check['suggest']:
                    print_suggestion(check['suggest'])
                return FAIL

    return PASS
