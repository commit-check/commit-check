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
from typing import Optional, Dict, Callable

from commit_check import branch, commit, author
from commit_check.error import error_handler
from commit_check.util import validate_config
from . import PASS, FAIL, __version__, DEFAULT_CONFIG


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


def _dispatch_checks_full(checks: list, stdin_text: Optional[str]) -> int:
    """Execute ALL configured checks once (used by future run mode)."""
    dispatcher: Dict[str, Callable[[], int]] = {
        'message': lambda: commit.check_commit_msg(checks, stdin_text=stdin_text),
        'imperative': lambda: commit.check_imperative(checks, stdin_text=stdin_text),
        'subject_capitalized': lambda: commit.check_subject_capitalized(checks, stdin_text=stdin_text),
        'subject_max_length': lambda: commit.check_subject_max_length(checks, stdin_text=stdin_text),
        'subject_min_length': lambda: commit.check_subject_min_length(checks, stdin_text=stdin_text),
        'allow_commit_types': lambda: commit.check_allow_commit_types(checks, stdin_text=stdin_text),
        'allow_merge_commits': lambda: commit.check_allow_merge_commits(checks, stdin_text=stdin_text),
        'allow_revert_commits': lambda: commit.check_allow_revert_commits(checks, stdin_text=stdin_text),
        'allow_empty_commits': lambda: commit.check_allow_empty_commits(checks, stdin_text=stdin_text),
        'allow_fixup_commits': lambda: commit.check_allow_fixup_commits(checks, stdin_text=stdin_text),
        'allow_wip_commits': lambda: commit.check_allow_wip_commits(checks, stdin_text=stdin_text),
        'commit_signoff': lambda: commit.check_commit_signoff(checks, stdin_text=stdin_text),
        'require_body': lambda: commit.check_require_body(checks, stdin_text=stdin_text),
        'branch': lambda: branch.check_branch(checks, stdin_text=stdin_text),
        'merge_base': lambda: branch.check_merge_base(checks),
        'author_name': lambda: author.check_author(checks, 'author_name', stdin_text=stdin_text),
        'author_email': lambda: author.check_author(checks, 'author_email', stdin_text=stdin_text),
        'allow_authors': lambda: author.check_allow_authors(checks, 'author_name', stdin_text=stdin_text),
        'ignore_authors': lambda: author.check_ignore_authors(checks, 'author_name', stdin_text=stdin_text),
        'commit_signoff_details': lambda: author.check_required_signoff_details(checks, stdin_text=stdin_text),
    }
    seen = set()
    results: list[int] = []
    for chk in checks:
        ctype = chk.get('check')
        if ctype in seen:
            continue
        seen.add(ctype)
        func = dispatcher.get(ctype)
        if func:
            res = func()
            results.append(res)
            if LOG_LEVEL == LogLevel.VERBOSE:
                log(f"[commit-check] {ctype} => {'OK' if res == PASS else 'FAIL'}")
    return PASS if not results else (PASS if all(r == PASS for r in results) else FAIL)


def main() -> int:
    argv = sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog='commit-check',
        description='check commit message, branch naming, committer name/email, commit signoff and more.'
    )
    parser.add_argument('command', choices=['run'], help="Only supported command: run")
    parser.add_argument('path', nargs='?', default='.', help='Repository path (default: current directory)')
    parser.add_argument('--config', type=str, default=None, help='Path to TOML configuration file (commit-check.toml or cchk.toml)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet logging')
    parser.add_argument('-s', '--silent', action='store_true', help='Silent mode')
    parser.add_argument('-V', '--version', action='store_true', help='Show version and exit')
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        raise SystemExit(0)

    # Command guard (argparse choices already enforce)
    if args.command != 'run':  # pragma: no cover
        parser.error("only 'run' is supported")

    set_log_level(args.verbose, args.quiet, args.silent)
    cfg_path = args.config or args.path
    stdin_text = _read_stdin()
    with error_handler():
        cfg = validate_config(cfg_path) or DEFAULT_CONFIG
        checks = cfg.get('checks', [])
        status = _dispatch_checks_full(checks, stdin_text=stdin_text)
        return status


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
