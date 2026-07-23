"""Modern commit-check CLI with clean architecture and TOML support."""

from __future__ import annotations
import json
import os
import sys
import argparse

from commit_check.config_merger import ConfigMerger, parse_bool, parse_list, parse_int
from commit_check.rule_builder import RuleBuilder
from commit_check.engine import (
    ValidationEngine,
    ValidationContext,
    ValidationResult,
    CheckOutcome,
)
from . import __version__


class StdinReader:
    """Handles stdin reading with proper error handling."""

    @staticmethod
    def read_piped_input() -> str | None:
        """Read commit message content if piped, with proper error handling."""
        try:
            if not sys.stdin.isatty():
                data = sys.stdin.read()
                return data.strip() if data else None
        except (OSError, IOError):
            return None
        return None


def _reconfigure_io() -> None:
    """Reconfigure stdout/stderr to UTF-8 so output never crashes on
    terminals with legacy encodings (e.g. GBK on Chinese Windows)."""
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _normalize_pre_commit_branch_ref(branch: str | None) -> str:
    """Return a full branch ref from a pre-commit branch environment value."""
    if not branch:
        return ""
    if branch.startswith("refs/"):
        return branch
    return f"refs/heads/{branch}"


def _build_pre_commit_push_input() -> str | None:
    """Build pre-push ref data from pre-commit's pre-push environment.

    pre-commit consumes git's native pre-push stdin and exposes the active push
    target through PRE_COMMIT_* variables. Convert that environment back into
    the same four-field format used by git's native pre-push hook.
    """
    remote_name = os.getenv("PRE_COMMIT_REMOTE_NAME") or os.getenv(
        "PRE_COMMIT_REMOTE_URL"
    )
    local_ref = _normalize_pre_commit_branch_ref(os.getenv("PRE_COMMIT_LOCAL_BRANCH"))
    remote_ref = _normalize_pre_commit_branch_ref(os.getenv("PRE_COMMIT_REMOTE_BRANCH"))
    local_sha = os.getenv("PRE_COMMIT_TO_REF") or ""
    remote_sha = ""

    if not (local_ref and remote_ref and local_sha):
        return None

    if remote_name:
        from commit_check.util import get_remote_branch_sha

        remote_branch = remote_ref.removeprefix("refs/heads/")
        remote_sha = get_remote_branch_sha(remote_name, remote_branch)

    remote_sha = remote_sha or os.getenv("PRE_COMMIT_FROM_REF") or ""

    if not remote_sha:
        return None

    return f"{local_ref} {local_sha} {remote_ref} {remote_sha}"


def _get_parser() -> argparse.ArgumentParser:
    """Get parser to interpret CLI args."""
    parser = argparse.ArgumentParser(
        prog="commit-check",
        description="Check commit message, branch name, author name, email, and more.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        help="path to config file (cchk.toml or commit-check.toml). If not specified, searches for config in: cchk.toml, commit-check.toml, .github/cchk.toml, .github/commit-check.toml",
    )

    parser.add_argument(
        "commit_msg_file",
        nargs="?",
        default=None,
        help="path to commit message file (positional argument for pre-commit compatibility)",
    )

    # Main check type arguments
    check_group = parser.add_argument_group(
        "check types", "Specify which validation checks to run"
    )

    check_group.add_argument(
        "-m",
        "--message",
        action="store_true",
        help="validate commit message (file path can be provided as positional argument for pre-commit compatibility)",
    )

    check_group.add_argument(
        "-b",
        "--branch",
        help="check current git branch name",
        action="store_true",
        required=False,
    )

    check_group.add_argument(
        "-n",
        "--author-name",
        help="check git author name",
        action="store_true",
        required=False,
    )

    check_group.add_argument(
        "-e",
        "--author-email",
        help="check git author email",
        action="store_true",
        required=False,
    )

    check_group.add_argument(
        "-d",
        "--dry-run",
        help="perform a dry run without failing (always returns 0)",
        action="store_true",
        required=False,
    )

    check_group.add_argument(
        "--no-force-push",
        help="check that no force push is being performed (uses pre-push hook stdin when available, otherwise checks the current branch against its upstream)",
        action="store_true",
        required=False,
    )

    check_group.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="output_format",
        metavar="FORMAT",
        help="output format: 'text' (default) for human-readable output, "
        "'json' for machine-readable JSON (useful for AI agents and tooling)",
    )

    check_group.add_argument(
        "--no-banner",
        action="store_true",
        default=False,
        help="suppress the ASCII art banner on failure",
    )

    check_group.add_argument(
        "--compact",
        action="store_true",
        default=False,
        help="show compact one-line-per-failure output (implies --no-banner)",
    )

    # Commit message configuration options
    commit_group = parser.add_argument_group(
        "commit message options", "Configuration options for --message validation"
    )

    commit_group.add_argument(
        "--conventional-commits",
        type=parse_bool,
        default=None,
        metavar="BOOL",
        help="enforce conventional commits format (true/false)",
    )

    commit_group.add_argument(
        "--subject-capitalized",
        type=parse_bool,
        default=None,
        metavar="BOOL",
        help="require subject to start with capital letter (true/false)",
    )

    commit_group.add_argument(
        "--subject-imperative",
        type=parse_bool,
        default=None,
        metavar="BOOL",
        help="require subject to use imperative mood (true/false)",
    )

    commit_group.add_argument(
        "--subject-max-length",
        type=parse_int,
        default=None,
        metavar="INT",
        help="maximum length of commit subject",
    )

    commit_group.add_argument(
        "--subject-min-length",
        type=parse_int,
        default=None,
        metavar="INT",
        help="minimum length of commit subject",
    )

    commit_group.add_argument(
        "--allow-commit-types",
        type=parse_list,
        default=None,
        metavar="LIST",
        help="comma-separated list of allowed commit types (e.g., feat,fix,docs)",
    )

    commit_group.add_argument(
        "--allow-merge-commits",
        type=parse_bool,
        default=None,
        metavar="BOOL",
        help="allow merge commits (true/false)",
    )

    commit_group.add_argument(
        "--allow-revert-commits",
        type=parse_bool,
        default=None,
        metavar="BOOL",
        help="allow revert commits (true/false)",
    )

    commit_group.add_argument(
        "--allow-empty-commits",
        type=parse_bool,
        default=None,
        metavar="BOOL",
        help="allow empty commit messages (true/false)",
    )

    commit_group.add_argument(
        "--allow-fixup-commits",
        type=parse_bool,
        default=None,
        metavar="BOOL",
        help="allow fixup commits (true/false)",
    )

    commit_group.add_argument(
        "--allow-wip-commits",
        type=parse_bool,
        default=None,
        metavar="BOOL",
        help="allow WIP commits (true/false)",
    )

    commit_group.add_argument(
        "--require-body",
        type=parse_bool,
        default=None,
        metavar="BOOL",
        help="require commit body (true/false)",
    )

    commit_group.add_argument(
        "--require-signed-off-by",
        type=parse_bool,
        default=None,
        metavar="BOOL",
        help="require 'Signed-off-by' trailer (true/false)",
    )

    commit_group.add_argument(
        "--ignore-authors",
        type=parse_list,
        default=None,
        metavar="LIST",
        help="comma-separated list of authors to ignore for commit checks",
    )

    commit_group.add_argument(
        "--ai-attribution",
        type=str,
        default=None,
        choices=["ignore", "forbid"],
        metavar="POLICY",
        help="AI attribution policy: ignore (default) or forbid. "
        "'forbid' rejects commits with known AI tool signatures.",
    )

    commit_group.add_argument(
        "--author-email-pattern",
        type=str,
        default=None,
        help="regex to check author email",
    )

    commit_group.add_argument(
        "--author-name-pattern",
        type=str,
        default=None,
        help="regex to check author name",
    )

    # Branch configuration options
    branch_group = parser.add_argument_group(
        "branch options", "Configuration options for --branch validation"
    )

    branch_group.add_argument(
        "--conventional-branch",
        type=parse_bool,
        default=None,
        metavar="BOOL",
        help="enforce conventional branch naming (true/false)",
    )

    branch_group.add_argument(
        "--allow-branch-types",
        type=parse_list,
        default=None,
        metavar="LIST",
        help="comma-separated list of allowed branch types (e.g., feature,bugfix,hotfix)",
    )

    branch_group.add_argument(
        "--allow-branch-names",
        type=parse_list,
        default=None,
        metavar="LIST",
        help="comma-separated list of additional allowed branch names",
    )

    branch_group.add_argument(
        "--require-rebase-target",
        type=str,
        default=None,
        metavar="BRANCH",
        help="target branch for rebase validation",
    )

    branch_group.add_argument(
        "--branch-ignore-authors",
        type=parse_list,
        default=None,
        metavar="LIST",
        help="comma-separated list of authors to ignore for branch checks",
    )

    return parser


def _resolve_commit_message_source(
    args: argparse.Namespace,
    stdin_reader: StdinReader,
) -> tuple[str | None, str | None]:
    """Determine commit message source: file path or stdin content.

    Returns a tuple of (stdin_content, commit_file_path).
    """
    if not args.message:
        return None, None

    if args.commit_msg_file:
        return None, args.commit_msg_file

    stdin_content = stdin_reader.read_piped_input()
    return stdin_content or None, None


def _resolve_stdin_for_non_message(
    args: argparse.Namespace, stdin_reader: StdinReader
) -> str | None:
    """Resolve stdin content for non-message validation types."""
    has_non_message_check = any(
        [args.branch, args.author_name, args.author_email, args.no_force_push]
    )
    if not has_non_message_check:
        return None

    stdin_content = stdin_reader.read_piped_input()
    if args.no_force_push and stdin_content is None:
        return _build_pre_commit_push_input()
    return stdin_content


def _get_requested_checks(args: argparse.Namespace) -> list[str]:
    """Build the list of requested validation checks based on CLI args."""
    requested_checks: list[str] = []

    if args.message:
        requested_checks.extend(
            [
                "message",
                "subject_imperative",
                "subject_max_length",
                "subject_min_length",
                "require_signed_off_by",
                "subject_capitalized",
                "require_body",
                "allow_merge_commits",
                "allow_revert_commits",
                "allow_empty_commits",
                "allow_fixup_commits",
                "allow_wip_commits",
                "ai_attribution",
            ]
        )
    if args.branch:
        requested_checks.extend(["branch", "merge_base"])
    if args.author_name:
        requested_checks.append("author_name")
    if args.author_email:
        requested_checks.append("author_email")
    if args.no_force_push:
        requested_checks.append("no_force_push")

    return requested_checks


def _run_json_output(engine: ValidationEngine, context: ValidationContext) -> int:
    """Run validation and print JSON output."""
    outcomes: list[CheckOutcome] = engine.validate_all_detailed(context)
    overall = "fail" if any(o.status == "fail" for o in outcomes) else "pass"
    print(
        json.dumps(
            {
                "status": overall,
                "checks": [o.to_dict() for o in outcomes],
            },
            indent=2,
        )
    )
    return 0 if overall == "pass" else 1


def main() -> int:
    """The main entrypoint of commit-check program."""
    _reconfigure_io()
    parser = _get_parser()
    args = parser.parse_args()

    if args.dry_run:
        return 0

    stdin_reader = StdinReader()

    try:
        # Handle positional commit_msg_file argument for pre-commit compatibility
        if args.commit_msg_file:
            args.message = True

        # Load and merge configuration from all sources: CLI > Env > TOML > Defaults
        config_data = ConfigMerger.from_all_sources(args, args.config)

        # When --no-force-push is explicitly passed, override allow_force_push to
        # False so the rule is built even if the TOML config defaults to True.
        if args.no_force_push:
            config_data.setdefault("push", {})["allow_force_push"] = False

        # Build validation rules from config
        rule_builder = RuleBuilder(config_data)
        all_rules = rule_builder.build_all_rules()

        # Determine which checks to run
        requested_checks = _get_requested_checks(args)
        if not requested_checks:
            parser.print_help()
            return 0

        # Filter rules to only include requested checks
        filtered_rules = [rule for rule in all_rules if rule.check in requested_checks]
        engine = ValidationEngine(filtered_rules)

        # Resolve validation context inputs
        stdin_content, commit_file_path = _resolve_commit_message_source(
            args, stdin_reader
        )
        if not args.message:
            stdin_content = _resolve_stdin_for_non_message(args, stdin_reader)

        # Reset banner state for this run
        from commit_check.util import print_error_header as _peh

        _peh.has_been_called = False

        context = ValidationContext(
            stdin_text=stdin_content,
            commit_file=commit_file_path,
            config=config_data,
            no_banner=getattr(args, "no_banner", False),
            compact=getattr(args, "compact", False),
            push_upstream_fallback=args.no_force_push and stdin_content is None,
        )

        # Run validation – choose output mode based on --format
        output_format: str = getattr(args, "output_format", "text")
        if output_format == "json":
            return _run_json_output(engine, context)

        result = engine.validate_all(context)
        return 0 if result == ValidationResult.PASS else 1

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
