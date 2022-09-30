"""
``commit_check.util``
---------------------

A module containing utility functions.
"""
import subprocess
from subprocess import CalledProcessError


CONFIG_FILE = '.commit-check.yml'


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
            f'git log origin/{get_branch_name()}..HEAD --pretty=format:"%s"',
        ).splitlines()
    except CalledProcessError:
        output = ''
    for output in outputs:
        commit_message.append(output)
    return commit_message


def cmd_output(*cmd: str) -> str:
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
