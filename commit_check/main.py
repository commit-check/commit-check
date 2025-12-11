"""Modern commit-check CLI with clean architecture and TOML support."""

from __future__ import annotations
import sys
import argparse
from typing import Optional

from commit_check.config import load_config
from commit_check.rule_builder import RuleBuilder
from commit_check.engine import ValidationEngine, ValidationContext, ValidationResult
from . import __version__


class StdinReader:
    """Handles stdin reading with proper error handling."""

    @staticmethod
    def read_piped_input() -> Optional[str]:
        """Read commit message content if piped, with proper error handling."""
        try:
            if not sys.stdin.isatty():
                data = sys.stdin.read()
                return data.strip() if data else None
        except (OSError, IOError):
            return None
        return None


def _get_parser() -> argparse.ArgumentParser:
    """Get parser to interpret CLI args."""
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
        help="path to config file (cchk.toml or commit-check.toml). If not specified, searches for cchk.toml in current directory",
    )

    parser.add_argument(
        "-m",
        "--message",
        nargs="?",
        const="",
        help="validate commit message. Optionally specify file path, otherwise reads from stdin if available",
    )

    parser.add_argument(
        "-b",
        "--branch",
        help="check current git branch name",
        action="store_true",
        required=False,
    )

    parser.add_argument(
        "-n",
        "--author-name",
        help="check git author name",
        action="store_true",
        required=False,
    )

    parser.add_argument(
        "-e",
        "--author-email",
        help="check git author email",
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


def _get_message_content(
    message_arg: Optional[str], stdin_reader: StdinReader
) -> Optional[str]:
    """Get commit message content from argument, file, or stdin."""
    if message_arg is None:
        return None

    # If message_arg is empty string (from nargs="?", const=""), try stdin first, then git
    if message_arg == "":
        # Try reading from stdin if available
        stdin_content = stdin_reader.read_piped_input()
        if stdin_content:
            return stdin_content

        # Fallback to latest git commit message
        try:
            from commit_check.util import get_commit_info

            return get_commit_info("B")  # Full commit message
        except Exception:
            print(
                "Error: No commit message provided and unable to read from git",
                file=sys.stderr,
            )
            return None

    # If message_arg is a file path, read from file
    try:
        with open(message_arg, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (OSError, IOError) as e:
        print(f"Error reading message file '{message_arg}': {e}", file=sys.stderr)
        return None


def main() -> int:
    """The main entrypoint of commit-check program."""
    parser = _get_parser()
    args = parser.parse_args()

    if args.dry_run:
        return 0

    stdin_reader = StdinReader()

    try:
        # Load configuration
        config_data = load_config(args.config)

        # Build validation rules from config
        rule_builder = RuleBuilder(config_data)
        all_rules = rule_builder.build_all_rules()

        # Filter rules based on CLI arguments
        requested_checks = []
        if (
            args.message is not None
        ):  # Check for None explicitly since empty string is valid
            # Add commit message related checks
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
                ]
            )
        if args.branch:
            requested_checks.extend(["branch", "merge_base"])
        if args.author_name:
            requested_checks.append("author_name")
        if args.author_email:
            requested_checks.append("author_email")

        # If no specific checks requested, show help
        if not requested_checks:
            parser.print_help()
            return 0

        # Filter rules to only include requested checks
        filtered_rules = [rule for rule in all_rules if rule.check in requested_checks]

        # Create validation engine with filtered rules
        engine = ValidationEngine(filtered_rules)

        # Create validation context
        stdin_content = None
        commit_file_path = None

        if (
            args.message is not None
        ):  # Check explicitly for None since empty string is valid
            if args.message == "":
                # Only set stdin_content if there's actual piped input
                stdin_content = stdin_reader.read_piped_input()
                if not stdin_content:
                    # No stdin and no file - let validators get data from git themselves
                    stdin_content = None
            else:
                # Message is a file path
                commit_file_path = args.message
        elif not any([args.branch, args.author_name, args.author_email]):
            # If no specific validation type is requested, don't read stdin
            pass
        else:
            # For non-message validations (branch, author), check for stdin input
            stdin_content = stdin_reader.read_piped_input()

        context = ValidationContext(
            stdin_text=stdin_content,
            commit_file=commit_file_path,
            config=config_data,
        )

        # Run validation
        result = engine.validate_all(context)

        # Return appropriate exit code
        return 0 if result == ValidationResult.PASS else 1

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
