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
        branch_name = cmd_output('git', 'rev-parse', '--abbrev-ref', 'HEAD')
    except CalledProcessError:
        branch_name = ''
    return branch_name


def get_commit_message() -> list:
    """Identify current commit message on local.

    :returns: A `list` message not be pushed to remote.
    """
    pass
    # commit_messages = []
    # commit_message = cmd_output('')


def cmd_output(*cmd: str) -> str:
    # proc = subprocess.Popen(cmd)
    # stdout, stderr = proc.communicate()
    # stdout = stdout.decode('utf-8')
    # if proc.returncode != 0:
    #     raise CalledProcessError(cmd, 1, proc.returncode, stdout, stderr)
    # return stdout
    pass
