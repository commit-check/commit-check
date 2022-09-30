"""
``commit_check.main``
---------------------

The module containing main entrypoint function.
"""
import argparse

from . import branch, message
from . import RESET_COLOR, YELLOW, VERSION


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
        '-b',
        '--branch',
        metavar='BRANCH',
        help='check git branch naming convention',
        type=str,
        default='',
        required=False,
    )

    parser.add_argument(
        '-m',
        '--message',
        metavar='MESSAGE',
        help='check commit message formatting convention',
        type=str,
        default='',
        required=False,
    )

    return parser


def main():
    """The main entrypoint of commit-check program."""
    parser = get_parser()
    args = parser.parse_args()
    if not args.message and not args.branch:
        print(
            f'\n{YELLOW}Nothing to do because `--message` and `--branch`',
            f'was not specified.{RESET_COLOR}\n',
        )
        parser.print_help()
    else:
        if args.message:
            message()
        if args.branch:
            branch()


if __name__ == '__main__':
    main()
