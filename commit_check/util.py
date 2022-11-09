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
        commands = ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
        branch_name = cmd_output(commands)
    except CalledProcessError:
        branch_name = ''
    return branch_name.strip()


def get_commits_info(format_string: str, number: int = 1) -> list:
    """Get commits information
    %s  - subject
    %ae - author email
    %an - author name

    :returns: A `list` info not be pushed to remote.
    """
    committer_info = []
    try:
        commands = [
            'git', 'log', '-n',
            f'{number}', f"--pretty=format:%{format_string}",
        ]
        outputs = cmd_output(commands).splitlines()
    except CalledProcessError:
        output = ''
    for output in outputs:
        if "Merge " in output:
            continue  # skip Merge 2066d into 4d89f
        committer_info.append(output)
    return committer_info


def cmd_output(commands: list) -> str:
    """Run command

    :returns: Get `str` message.
    """
    result = subprocess.run(
        commands, capture_output=True, encoding='utf-8',
    )
    if result.returncode == 0 and result.stdout is not None:
        return result.stdout
    elif result.stderr != '':
        return result.stderr
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
