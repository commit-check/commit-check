"""
``commit_check.error``
---------------------

A module containing error handler functions.
"""
import contextlib
import os
import sys
import traceback
from typing import Generator
from commit_check.util import cmd_output


@contextlib.contextmanager
def error_handler() -> Generator[None, None, None]:
    try:
        yield
    except (Exception, KeyboardInterrupt) as e:
        if isinstance(e, RuntimeError):
            msg, ret_code = 'An error has occurred', 1
        elif isinstance(e, KeyboardInterrupt):
            msg, ret_code = 'Interrupted (^C)', 130
        else:
            msg, ret_code = 'An unexpected error has occurred', 3
        log_and_exit(msg, ret_code, e, traceback.format_exc())


def log_and_exit(msg: str, ret_code: int, exc: BaseException, formatted: str) -> None:
    error_msg = f'{msg}: {type(exc).__name__}: {exc}'
    commit_check_version = cmd_output(['commit-check', '--version'])
    git_version = cmd_output(['git', '--version'])

    store_dir = os.environ.get('COMMIT_CHECK_HOME') or os.path.join(
        os.environ.get('XDG_CACHE_HOME') or os.path.expanduser('~/.cache'),
        'commit-check',
    )
    log_path = os.path.join(store_dir, 'commit-check.log')
    if not os.path.exists(store_dir):
        os.makedirs(store_dir, exist_ok=True)
        with open(os.path.join(store_dir, 'README'), 'w') as f:
            f.write(
                'This directory is maintained by the commit-check project.\n'
                'Learn more: https://github.com/commit-check/commit-check\n',
            )

    def write_line(log_ctx=""):
        with open(log_path, 'a') as file:
            file.write(f'{log_ctx}\n')

    if os.access(store_dir, os.W_OK):
        open(log_path, 'w').close()
        write_line('### version information')
        write_line('```')
        write_line(f'commit-check --version: {commit_check_version}')
        write_line(f'git --version: {git_version}')
        write_line('sys.version:')
        for line in sys.version.splitlines():
            write_line(f'    {line}')
        write_line(f'sys.executable: {sys.executable}')
        write_line(f'os.name: {os.name}')
        write_line(f'sys.platform: {sys.platform}')
        write_line('```')
        write_line()
        write_line('### error information')
        write_line()
        write_line('```')
        write_line(error_msg)
        write_line('```')
        write_line()
        write_line('```')
        write_line(formatted.rstrip())
        write_line('```')
    else:
        write_line(f'Failed to write to log at {log_path}')

    print(error_msg)
    print(f'Check the log at {log_path}')

    raise SystemExit(ret_code)
