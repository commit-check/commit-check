"""
``commit_check.main``
---------------------

The module containing main entrypoint function.
"""
import argparse

from commit_check import branch
from commit_check import commit
from commit_check import config as git_config
from commit_check.util import validate_config, get_version
from . import RESET_COLOR, YELLOW, CONFIG_FILE, DEFAULT_CONFIG, PASS


def get_parser() -> argparse.ArgumentParser:
    """Get and parser to interpret CLI args."""
    parser = argparse.ArgumentParser(
        prog='commit-check',
        description="Check commit message, branch naming, committer name, email, and more."
    )

    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=f'%(prog)s {get_version()}',
    )

    parser.add_argument(
        '-c',
        '--config',
        default=CONFIG_FILE,
        help='path to config file. default is .',
    )

    parser.add_argument(
        '-m',
        '--message',
        help='check commit message',
        action="store_true",
        required=False,
    )

    parser.add_argument(
        '-b',
        '--branch',
        help='check branch naming',
        action="store_true",
        required=False,
    )

    parser.add_argument(
        '-n',
        '--author-name',
        help='check committer\'s name',
        action="store_true",
        required=False,
    )

    parser.add_argument(
        '-e',
        '--author-email',
        help='check committer\'s email',
        action="store_true",
        required=False,
    )

    parser.add_argument(
        '-d',
        '--dry-run',
        help='run checks without failing',
        action="store_true",
        required=False,
    )

    return parser


def main() -> int:
    """The main entrypoint of commit-check program."""
    parser = get_parser()
    args = parser.parse_args()
    retval = PASS

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
        checks = config['checks']
        if args.message:
            retval = commit.check_commit(checks)
        if args.author_name:
            retval = git_config.check_git_config(checks, "author_name")
        if args.author_email:
            retval = git_config.check_git_config(checks, "author_email")
        if args.branch:
            retval = branch.check_branch(checks)

    if args.dry_run:
        retval = PASS
    return retval


if __name__ == '__main__':
    raise SystemExit(main())  # pragma: no cover
