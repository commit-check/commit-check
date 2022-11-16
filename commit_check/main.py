"""
``commit_check.main``
---------------------

The module containing main entrypoint function.
"""
import argparse

from commit_check import branch
from commit_check import commit
from commit_check import config as git_config
from commit_check.util import validate_config
from . import RESET_COLOR, YELLOW, VERSION, CONFIG_FILE, DEFAULT_CONFIG, PASS, FAIL


def get_parser() -> argparse.ArgumentParser:
    """Get and parser to interpret CLI args."""
    parser = argparse.ArgumentParser(prog='commit-check')

    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=f'%(prog)s {VERSION}',
    )

    parser.add_argument(
        '-c',
        '--config',
        default=CONFIG_FILE,
        help='path to alternate config file. default is the current path',
    )

    parser.add_argument(
        '-m',
        '--message',
        help=(
            'check commit message formatting convention. '
            'overwrite the config file if specified. '
            'by default follow conventional commits https://www.conventionalcommits.org'
        ),
        action="store_true",
        required=False,
    )

    parser.add_argument(
        '-b',
        '--branch',
        help=(
            'check git branch naming convention. overwrite the config file if specified. '
            'by default follow bitbucket branching model.'
        ),
        action="store_true",
        required=False,
    )

    parser.add_argument(
        '-e',
        '--author-email',
        help=(
            'check committer author email. overwrite the config file if specified. '
            'by default check general email address.'
        ),
        action="store_true",
        required=False,
    )

    parser.add_argument(
        '-a',
        '--author-name',
        help=(
            'check committer author name. overwrite the config file if specified. '
            'No check by default'
        ),
        action="store_true",
        required=False,
    )

    parser.add_argument(
        '-n',
        '--no-verify',
        help='bypasses all commit checks',
        action="store_true",
        required=False,
    )

    return parser


def main() -> int:
    """The main entrypoint of commit-check program."""
    parser = get_parser()
    args = parser.parse_args()
    retval = PASS
    if args.no_verify:
        return FAIL
    if not any([args.message, args.branch, args.author_name, args.author_email]):
        print(
            f'\n{YELLOW}Nothing to do because `--message`, `--branch`, `--author-name`, `--author-email`',
            f'was not specified.{RESET_COLOR}\n',
        )
        parser.print_help()
    else:
        config = validate_config(args.config) if validate_config(
            args.config,
        ) else DEFAULT_CONFIG
        if args.message:
            retval = commit.check_commit(config)
        if args.author_name:
            retval = git_config.check_config(config, "author_name")
        if args.author_email:
            retval = git_config.check_config(config, "author_email")
        if args.branch:
            retval = branch.check_branch(config)
    return retval


if __name__ == '__main__':
    raise SystemExit(main())
