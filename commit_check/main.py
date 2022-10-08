"""
``commit_check.main``
---------------------

The module containing main entrypoint function.
"""
import argparse

from commit_check import branch
from commit_check import message
from commit_check.util import validate_config
from . import RESET_COLOR, YELLOW, VERSION, CONFIG_FILE, DEFAULT_CONFIG


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
        help='path to alternate config file',
    )

    parser.add_argument(
        '-m',
        '--message',
        help=(
            'check commit message formatting convention. '
            'overwrite the config file if specified. '
            'by default follow conventional commits https://www.conventionalcommits.org '
            'when config file not exist.'
        ),
        type=str,
        default='',
        required=False,
    )

    parser.add_argument(
        '-b',
        '--branch',
        help='check git branch naming convention. overwrite the config file if specified.',
        type=str,
        default='',
        required=False,
    )

    parser.add_argument(
        '-n',
        '--no-verify',
        help='bypasses commit-check.',
        action="store_true",
        required=False,
    )

    return parser


def main():
    """The main entrypoint of commit-check program."""
    parser = get_parser()
    args = parser.parse_args()
    if args.no_verify:
        return
    if not any([args.message, args.branch, validate_config()]):
        print(
            f'\n{YELLOW}Nothing to do because `--message` and `--branch`',
            f'was not specified.{RESET_COLOR}\n',
        )
        parser.print_help()
    else:
        config = DEFAULT_CONFIG
        if args.config:
            config = validate_config()
        if args.message:
            message.check_message(config)
        if args.branch:
            branch.check_branch(config)


if __name__ == '__main__':
    main()
