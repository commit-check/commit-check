"""
``commit_check.util``
---------------------

A module containing utility functions.
"""
import subprocess
import yaml
from pathlib import PurePath
from subprocess import CalledProcessError
from commit_check import RED, RESET_COLOR


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


def get_commits_info(format_string) -> list:
    """Get commits information
    %s  - subject
    %ae - author email
    %an - author name

    :returns: A `list` info not be pushed to remote.
    """
    committer_info = []
    try:
        outputs = cmd_output(
            f'git log --branches --not --remotes --pretty=format:"%{format_string}"',
        ).splitlines()
    except CalledProcessError:
        output = ''
    for output in outputs:
        committer_info.append(output)
    return committer_info


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


def validate_config(path_to_config: str) -> dict:
    """Validate config file.

    :returns: Get `dict` value if exist else get empty.
    """
    configuration = {}
    try:
        with open(PurePath(path_to_config)) as f:
            configuration = yaml.safe_load(f)
    except FileNotFoundError:
        pass
    return configuration


def print_error_message(check: str, regex: str, error: str, checkpoint: str):
    """Print error message.

    : returns: Give error messages to user
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
    if check == "commit_message":
        print(
            f"Invalid commit message => {RED}{checkpoint}{RESET_COLOR} ", end='',
        )
    elif check == "branch_name":
        print(
            f"Invalid branch name => {RED}{checkpoint}{RESET_COLOR} ", end='',
        )
    elif check == "author_email":
        print(
            f"Invalid email address => {RED}{checkpoint}{RESET_COLOR} ", end='',
        )
    elif check == "author_name":
        print(
            f"Invalid author name => {RED}{checkpoint}{RESET_COLOR} ", end='',
        )
    else:
        print(f"commit-check does not support {check} yet.")
        raise SystemExit(1)
    print(f"\nIt does't match regex: {regex}")
    print("")
    print(error)
