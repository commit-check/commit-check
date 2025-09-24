"""Minimal argparse CLI.

Only command: run

Usage:
    commit-check run [PATH] [--config FILE] [-v|-q|-s] [--version]

Behavior: loads config and executes every defined check exactly once.
Exit codes: 0 all pass, 1 any fail.
"""

from __future__ import annotations
import sys
import argparse
from typing import Optional

from commit_check import branch, commit, author
from commit_check.error import error_handler
from commit_check.util import validate_config
from . import CONFIG_FILE, PASS, FAIL, __version__, DEFAULT_CONFIG


class LogLevel:
    VERBOSE = 3
    QUIET = 1
    SILENT = 0
    NORMAL = 2


LOG_LEVEL = LogLevel.NORMAL


def set_log_level(verbose: bool, quiet: bool, silent: bool) -> None:
    global LOG_LEVEL
    # Mutual exclusivity: priority silent > verbose > quiet > normal
    if silent:
        LOG_LEVEL = LogLevel.SILENT
    elif verbose:
        LOG_LEVEL = LogLevel.VERBOSE
    elif quiet:
        LOG_LEVEL = LogLevel.QUIET
    else:
        LOG_LEVEL = LogLevel.NORMAL


def log(msg: str, level: int = LogLevel.NORMAL) -> None:
    if LOG_LEVEL == LogLevel.SILENT:
        return
    if LOG_LEVEL == LogLevel.QUIET and level > LogLevel.QUIET:
        return
    print(msg)


def _read_stdin() -> Optional[str]:  # read commit message content if piped
    try:
        if not sys.stdin.isatty():
            data = sys.stdin.read()
            return data or None
    except Exception:
        return None
    return None


def _get_parser() -> argparse.ArgumentParser:
    """Get and parser to interpret CLI args."""
    parser = argparse.ArgumentParser(
        prog="commit-check",
        description="Check commit message, branch name, author name, email, and more.",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "-c",
        "--config",
        default=CONFIG_FILE,
        help="path to config file. default is . (current directory)",
    )

    parser.add_argument(
        "-m",
        "--message",
        help="check commit message",
        action="store_true",
        required=False,
    )

    parser.add_argument(
        "-i",
        "--imperative",
        help="check commit message starts with imperative verb",
        action="store_true",
        required=False,
    )

    parser.add_argument(
        "-b",
        "--branch",
        help="check branch name",
        action="store_true",
        required=False,
    )

    parser.add_argument(
        "-n",
        "--author-name",
        help="check author name",
        action="store_true",
        required=False,
    )

    parser.add_argument(
        "-e",
        "--author-email",
        help="check author email",
        action="store_true",
        required=False,
    )

    parser.add_argument(
        "-s",
        "--signoff",
        help="check author signoff",
        action="store_true",
        required=False,
    )

    parser.add_argument(
        "--merge-base",
        help="check if branch is ahead of main branch",
        action="store_true",
        required=False,
    )

    parser.add_argument(
        "-d",
        "--dry-run",
        help="perform a dry run without failing (always returns 0)",
        action="store_true",
        required=False,
    )

    return parser


def main() -> int:
    """The main entrypoint of commit-check program."""
    parser = _get_parser()
    args = parser.parse_args()

    if args.dry_run:
        return PASS

    # Capture stdin (if piped) once and pass to checks.
    stdin_text = None
    try:
        if not sys.stdin.isatty():
            data = sys.stdin.read()
            stdin_text = data or None
    except Exception:
        stdin_text = None

    check_results: list[int] = []

    with error_handler():
        config = (
            validate_config(args.config)
            if validate_config(
                args.config,
            )
            else DEFAULT_CONFIG
        )
        checks = config["checks"]
        if args.message:
            check_results.append(commit.check_commit_msg(checks, stdin_text=stdin_text))
        if args.branch:
            check_results.append(branch.check_branch(checks, stdin_text=stdin_text))
        if args.author_name:
            check_results.append(
                author.check_author(checks, "author_name", stdin_text=stdin_text)
            )
        if args.author_email:
            check_results.append(
                author.check_author(checks, "author_email", stdin_text=stdin_text)
            )
        if args.signoff:
            check_results.append(commit.check_signoff(checks, stdin_text=stdin_text))
        if args.merge_base:
            check_results.append(branch.check_merge_base(checks))
        if args.imperative:
            check_results.append(commit.check_imperative(checks, stdin_text=stdin_text))

    return PASS if all(val == PASS for val in check_results) else FAIL


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
