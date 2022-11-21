"""
``commit_check.util``
---------------------

A module containing utility functions.
"""
import subprocess
import yaml
from pathlib import PurePath
from subprocess import CalledProcessError
from commit_check import RED, GREEN, RESET_COLOR


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


def get_commits_info(format_string: str) -> str:
    """Get latest commits information
    format_string could be
        %s  - subject
        %ae - author email
        %an - author name

    :returns: A `str`.
    """
    try:
        commands = [
            'git', 'log', '-n',
            '-1', f"--pretty=format:%{format_string}",
        ]
        output = str(cmd_output(commands).splitlines())
    except CalledProcessError:
        output = ''
    return output


def get_config(config_name: str) -> str:
    """Get git config.

    :returns: A `str` of the config value
    """
    try:
        commands = ['git', 'config', f"{config_name}"]
        config_value = cmd_output(commands)
    except CalledProcessError:
        config_value = ''
    return config_value.strip()


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


def print_error_message(check_type: str, regex: str, error: str, error_point: str):
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
    if check_type == "commit_message":
        print(
            f"Invalid commit message => {RED}{error_point}{RESET_COLOR} ", end='',
        )
    elif check_type == "branch_name":
        print(
            f"Invalid branch name => {RED}{error_point}{RESET_COLOR} ", end='',
        )
    elif check_type == "author_name":
        print(
            f"Invalid author name => {RED}{error_point}{RESET_COLOR} ", end='',
        )
    elif check_type == "author_email":
        print(
            f"Invalid email address => {RED}{error_point}{RESET_COLOR} ", end='',
        )
    else:
        print(f"commit-check does not support {check_type} yet.")
        raise SystemExit(1)
    print(f"\nIt does't match regex: {regex}")
    print("")
    print(error)


def print_suggestion(suggest: str):
    if suggest:
        print(
            f"Suggest to run => {GREEN}{suggest}{RESET_COLOR} ", end='',
        )
    else:
        print(f"commit-check does not support {suggest} yet.")
        raise SystemExit(1)
    print('\n')
