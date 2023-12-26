"""
``commit_check.main``
---------------------

The module containing main entrypoint function.
"""
import argparse
from commit_check import branch
from commit_check import commit
from commit_check import author
from commit_check.util import validate_config
from commit_check.error import error_handler
from . import CONFIG_FILE, DEFAULT_CONFIG, PASS, __version__


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
        version=f'%(prog)s {__version__}',
    )

    parser.add_argument(
        '-c',
        '--config',
        default=CONFIG_FILE,
        help='path to config file. default is . (current directory)',
    )

    parser.add_argument(
        '-m',
        '--message',
        help='check commit message',
        action="store_true",
        required=False,
    )

    parser.add_argument('commit_msg_file', nargs='?', help='commit message file')

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
        '-s',
        '--commit-signoff',
        help='check committer\'s signature',
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

    with error_handler():
        config = validate_config(args.config) if validate_config(
            args.config,
        ) else DEFAULT_CONFIG
        checks = config['checks']
        if args.message:
            retval = commit.check_commit_msg(checks, args.commit_msg_file)
        if args.author_name:
            retval = author.check_author(checks, "author_name")
        if args.author_email:
            retval = author.check_author(checks, "author_email")
        if args.branch:
            retval = branch.check_branch(checks)
        if args.commit_signoff:
            retval = commit.check_commit_signoff(checks)

    if args.dry_run:
        retval = PASS
    return retval


if __name__ == '__main__':
    raise SystemExit(main())  # pragma: no cover
