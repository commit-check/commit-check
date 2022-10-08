"""
``commit_check.util``
---------------------

A module containing utility functions.
"""
import subprocess
import yaml
from subprocess import CalledProcessError
from commit_check import CONFIG_FILE, RED, RESET_COLOR


def get_branch_name() -> str:
    """Identify current branch name.
    .. note::
        With Git 2.22 and above supports `git branch --show-current`
        Please open an issue at https://github.com/commit-check/commit-check/issues
        if you encounter any issue.

    :returns: A `str` describing the current branch name.
    """
    try:
        branch_name = cmd_output('git rev-parse --abbrev-ref HEAD')
    except CalledProcessError:
        branch_name = ''
    return branch_name.strip()


def get_commit_message() -> list:
    """Identify current commit message on local.

    :returns: A `list` message not be pushed to remote.
    """
    commit_message = []
    try:
        outputs = cmd_output(
            'git log --branches --not --remotes --pretty=format:"%s"',
        ).splitlines()
    except CalledProcessError:
        output = ''
    for output in outputs:
        commit_message.append(output)
    return commit_message


def cmd_output(*cmd: str) -> str:
    """Run command

    :returns: Get `str` message.
    """
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8',
    )
    stdout, stderr = process.communicate()
    if process.returncode == 0 and stdout is not None:
        return stdout
    elif stderr != '':
        return stderr
    else:
        return ''


def validate_config() -> dict:
    """Validate config file.

    :returns: Get `dict` value if exist else get empty.
    """
    configuration = {}
    try:
        with open(CONFIG_FILE) as f:
            configuration = yaml.safe_load(f)
    except FileNotFoundError:
        pass
    return configuration


def error_tips(check: str, regex: str, error: str, checkpoint: str):
    """Output error message.

    : returns: Give an error message to user
    """
    print("Commit rejected by Commit-Check.                                  ")
    print("                                                                  ")
    print(r"  (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)  ")
    print(r"   / ._. \      / ._. \      / ._. \      / ._. \      / ._. \   ")
    print(r" __\( C )/__  __\( H )/__  __\( E )/__  __\( C )/__  __\( K )/__ ")
    print(r"(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)")
    print(r"   || E ||      || R ||      || R ||      || O ||      || R ||   ")
    print(r" _.' `-' '._  _.' `-' '._  _.' `-' '._  _.' `-' '._  _.' `-' '.  ")
    print(r"(.-./`-'\.-.)(.-./`-`\.-.)(.-./`-`\.-.)(.-./`-'\.-.)(.-./`-`\.-.)")
    print(r" `-'     `-'  `-'     `-'  `-'     `-'  `-'     `-'  `-'     `-' ")
    print("                                                                  ")
    print("Commit rejected.                                                  ")
    print("                                                                  ")
    if check == "message":
        print(
            f"Invalid commit message => {RED}{checkpoint}{RESET_COLOR} ", end='',
        )
    elif check == "branch":
        print(
            f"Invalid branch name => {RED}{checkpoint}{RESET_COLOR} ", end='',
        )
    else:
        print(f"commit-check does not support {check} yet.")
        SystemExit(1)
    print(f"\nIt does't match regex: {regex}")
    print("")
    print(error)
