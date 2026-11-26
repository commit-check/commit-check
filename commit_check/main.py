"""Modern commit-check CLI with clean architecture and TOML support."""

from __future__ import annotations

import argparse
import json
import os
import select
import sys

from commit_check.config import ConfigError, find_config_path, report_notice
from commit_check.config_merger import ConfigMerger, parse_bool, parse_int, parse_list
from commit_check.engine import (
    CheckOutcome,
    ValidationContext,
    ValidationEngine,
    ValidationResult,
    ai_tools_in,
    count_warnings,
    overall_status,
)
from commit_check.rule_builder import RuleBuilder
from commit_check.rules_catalog import (
    AI_TEXT_CHECKS,
    BRANCH_CHECKS,
    FILES_CHECKS,
    MESSAGE_CHECKS,
    PR_TITLE_CHECKS,
)
from commit_check.util import (
    get_remote_branch_sha,
    git_repository_error,
    git_rev_parse_verify,
    print_error_header,
    split_message_comments,
)

from . import AI_ATTRIBUTION_POLICIES, BOLD, DIM, RESET_COLOR

# Exit codes. ``1`` is a verdict on the commit; ``2`` means the run could not
# be set up at all -- the same code argparse uses for a bad command line -- so
# a wrapper can tell a rejected commit from a broken configuration.
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_CONFIG_ERROR = 2


class StdinReader:
    """Handles stdin reading with proper error handling."""

    @staticmethod
    def _has_pending_data(timeout: float) -> bool:
        """Whether reading stdin would return promptly rather than block.

        ``read()`` on a pipe that is open but has no writer about to close it
        blocks forever. That is what stdin looks like under some CI runners
        and process managers, so an unconditional read turns "nothing was
        piped" into a hang — the step neither fails nor finishes.

        ``select`` distinguishes the two: piped input is already in the pipe
        buffer by the time this process is exec'd (and EOF, as with
        ``< /dev/null``, counts as readable), while an idle pipe is not
        readable and never will be. The timeout is margin, not a wait.
        """
        if sys.platform == "win32":  # pragma: no cover
            # select() only works on sockets on Windows. Keep the historic
            # blocking read there; the hang has only been observed on POSIX
            # runners, and a wrong guess here would break piping instead.
            return True

        try:
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
        except (OSError, ValueError):
            # No usable stdin descriptor at all: nothing to read.
            return False
        return bool(ready)

    @classmethod
    def read_piped_input(cls) -> str | None:
        """Read commit message content if piped, with proper error handling."""
        try:
            if not sys.stdin.isatty() and cls._has_pending_data(timeout=0.1):
                data = sys.stdin.read()
                return data.strip() if data else None
        except OSError:
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
        remote_branch = remote_ref.removeprefix("refs/heads/")
        remote_sha = get_remote_branch_sha(remote_name, remote_branch)

    remote_sha = remote_sha or os.getenv("PRE_COMMIT_FROM_REF") or ""

    if not remote_sha:
        return None

    return f"{local_ref} {local_sha} {remote_ref} {remote_sha}"


class _VersionAction(argparse.Action):
    """``--version``, with the version looked up only when it is asked for.

    Reading the package metadata costs more than the rest of startup, so the
    parser must not do it on every run just to have the string ready.
    """

    def __init__(self, option_strings: list[str], dest: str, **kwargs: object) -> None:
        super().__init__(
            option_strings,
            dest=argparse.SUPPRESS,
            default=argparse.SUPPRESS,
            nargs=0,
            help="show program's version number and exit",
        )

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: str | None = None,
    ) -> None:
        from . import __version__

        print(f"{parser.prog} {__version__}")
        parser.exit()


def _print_intro(config: str | None) -> None:
    """What a bare ``commit-check`` prints: one screen, not the full help.

    Someone who types the name to see what it is gets the version, the few
    commands that cover most uses, which config the run would read and where
    the docs are. ``--help`` still lists every option.
    """
    from . import __version__

    examples = (
        ("commit-check -m -b", "check the last commit message and the branch"),
        ("commit-check -m < msg.txt", "check a message before you commit it"),
        ("commit-check --help", "list every option"),
    )
    width = max(len(cmd) for cmd, _ in examples)
    title = f"{BOLD}Commit Check{RESET_COLOR} {__version__}"
    lines = [f"{title}{DIM} · commit policy as code{RESET_COLOR}", ""]
    lines += [
        f"  {cmd.ljust(width)}   {DIM}{what}{RESET_COLOR}" for cmd, what in examples
    ]
    lines.append("")
    found = find_config_path(config or "")
    if found:
        lines.append(f"  {DIM}Config{RESET_COLOR}  {os.path.relpath(found)}")
    else:
        lines.append(
            f"  {DIM}Config{RESET_COLOR}  none found, using the defaults: Conventional Commits,"
        )
        lines.append("          Conventional Branch, subjects up to 80 characters")
    lines.append(
        f"  {DIM}Docs{RESET_COLOR}    https://commit-check.com/getting-started/"
    )
    print("\n".join(lines))


def _get_parser() -> argparse.ArgumentParser:
    """Get parser to interpret CLI args."""
    parser = argparse.ArgumentParser(
        prog="commit-check",
        usage="%(prog)s [options] [commit_msg_file]",
        description="Check commit message, branch name, author name, email, and more.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "exit codes:\n"
            "  0  every enforced check passed, or --dry-run was given\n"
            "  1  a check failed\n"
            "  2  the run could not start: bad usage, a missing or invalid "
            "config file, or git cannot read the repository"
        ),
    )

    parser.add_argument(
        "-v",
        "--version",
        action=_VersionAction,
    )

    parser.add_argument(
        "-c",
        "--config",
        help="path to config file (cchk.toml or commit-check.toml). If not specified, searches for config in: cchk.toml, commit-check.toml, .github/cchk.toml, .github/commit-check.toml",
    )

    parser.add_argument(
        "--rev",
        metavar="REVISION",
        default=None,
        help="check the commit at this git revision (e.g. HEAD^2, a SHA) "
        "instead of HEAD or the working state. Message checks read that "
        "commit's message; author checks read that commit's author, not "
        "the local git config",
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
        "--ai-attribution-only",
        action="store_true",
        help="check only the AI attribution of the message (CC013 to CC016), "
        "for text that is not a commit message, such as a pull request "
        "description, and its AI declaration when [pull_request] "
        "ai_declaration_checkboxes is set (CC501); implies --message",
    )
    check_group.add_argument(
        "--pr-title",
        action="store_true",
        help="check a pull or merge request title piped on stdin against the "
        "message rules a one-line title can meet: every --message rule but a "
        "body (CC011), a sign-off (CC012) and an AI author (CC017); implies "
        "--message",
    )
    # The name it shipped with in 2.20.1, kept so existing scripts still work.
    check_group.add_argument(
        "--ai-only",
        dest="ai_attribution_only",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    check_group.add_argument(
        "-b",
        "--branch",
        help="check current git branch name",
        action="store_true",
        required=False,
    )

    check_group.add_argument(
        "-t",
        "--tag",
        help="check the name of the tag(s) pointing at HEAD (or --rev); "
        "a commit with no tag is reported as skipped",
        action="store_true",
        required=False,
    )

    check_group.add_argument(
        "-f",
        "--files",
        help="check the files the commit at HEAD (or --rev) touches: size "
        "limit, prohibited path patterns, path length, paths a commit "
        "attributed to an AI tool may not change (all off until configured "
        "in the [files] config section)",
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
        help="run every check and print the findings, but exit 0 even when "
        "one fails; a configuration error still exits 2",
        action="store_true",
        required=False,
    )

    parser.add_argument(
        "--fix",
        help="rewrite the commit message file when every failed message check "
        "has a mechanical fix, such as a type's case or a missing colon",
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
        help="suppress the one-line rejection header on failure",
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
        help="maximum length of commit subject; 0 turns the check off",
    )

    commit_group.add_argument(
        "--subject-min-length",
        type=parse_int,
        default=None,
        metavar="INT",
        help="minimum length of commit subject; 0 turns the check off",
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
        help="allow fixup!, squash! and amend! commits (true/false)",
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
        "--body-max-line-length",
        type=parse_int,
        default=None,
        metavar="INT",
        help="maximum length of a commit body line; 0 (the default) turns the check off",
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
        choices=list(AI_ATTRIBUTION_POLICIES),
        metavar="POLICY",
        help="AI attribution policy: ignore (default), forbid or disclose. "
        "'forbid' rejects commits with known AI tool signatures; 'disclose' "
        "accepts AI assistance disclosed with an accepted trailer and "
        "rejects the tool as a co-author or a sign-off.",
    )

    commit_group.add_argument(
        "--ai-disclosure-trailers",
        type=parse_list,
        default=None,
        metavar="LIST",
        help="comma-separated trailers that disclose AI assistance under "
        "--ai-attribution=disclose (default: Assisted-by,Generated-by)",
    )

    commit_group.add_argument(
        "--ai-disclosure-pattern",
        type=str,
        default=None,
        metavar="REGEX",
        help="regex the value of an AI disclosure trailer must match "
        "(e.g. '^\\S+/\\S+' for agent/model); empty accepts any value",
    )

    commit_group.add_argument(
        "--author-email-pattern",
        type=str,
        default=None,
        metavar="REGEX",
        help="regex to check author email (requires --author-email)",
    )

    commit_group.add_argument(
        "--author-name-pattern",
        type=str,
        default=None,
        metavar="REGEX",
        help="regex to check author name (requires --author-name)",
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
        "--require-description-grammar",
        type=parse_bool,
        default=None,
        metavar="BOOL",
        help="hold the description after '/' to the Conventional Branch grammar "
        "(true/false)",
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

    # Tag configuration options
    tag_group = parser.add_argument_group(
        "tag options", "Configuration options for --tag validation"
    )

    tag_group.add_argument(
        "--tag-regex",
        type=str,
        default=None,
        metavar="REGEX",
        help="pattern tag names must match (default: SemVer with an optional "
        "leading v, e.g. v1.2.3); an empty value disables the pattern match",
    )

    # Files configuration options
    files_group = parser.add_argument_group(
        "files options", "Configuration options for --files validation"
    )

    files_group.add_argument(
        "--files-max-size",
        type=str,
        default=None,
        metavar="SIZE",
        help="maximum size for a committed file, in bytes or with a unit "
        "suffix (e.g. 5MB, 500KB)",
    )

    files_group.add_argument(
        "--files-prohibited-patterns",
        type=parse_list,
        default=None,
        metavar="LIST",
        help="comma-separated fnmatch patterns committed paths must not "
        "match (e.g. *.pem,.env,id_rsa*); a bare pattern also matches "
        "the file name at any depth",
    )

    files_group.add_argument(
        "--files-max-path-length",
        type=int,
        default=None,
        metavar="INT",
        help="maximum number of characters in a committed file path",
    )

    files_group.add_argument(
        "--files-ai-prohibited-patterns",
        type=parse_list,
        default=None,
        metavar="LIST",
        help="comma-separated fnmatch patterns for paths a commit attributed "
        "to an AI tool must not change (e.g. .github/workflows/*,CODEOWNERS); "
        "deleting or renaming a path counts as changing it",
    )

    return parser


def _fix_message_file(path: str, rules: list, config: dict) -> None:
    """Rewrite a commit message file when every failure in it has a fix.

    A subject rule's fix is the corrected subject; every other rule's fix is
    the corrected message. Fixes go in one at a time, re-checking after
    each, and a failure no fix can reach leaves the file as it was.
    """
    with open(path, encoding="utf-8") as f:
        original = f.read()
    message, comments = split_message_comments(original)
    message = message.strip()
    engine = ValidationEngine([r for r in rules if r.check in MESSAGE_CHECKS])
    fixed = []
    for _ in range(len(engine.rules) + 1):
        context = ValidationContext(
            stdin_text=message, stdin_is_message=True, config=config
        )
        outcomes = engine.validate_all_detailed(context)
        failed = [o for o in outcomes if o.status == "fail"]
        fixable = [o for o in failed if o.fix]
        if not fixable:
            break
        first = fixable[0]
        subject = message.split("\n", 1)[0]
        if first.value == subject:
            message = first.fix + message[len(subject) :]
        else:
            message = first.fix
        fixed.append(f"{first.rule_id} {first.check.replace('_', '-')}")
    if failed or not fixed:
        return
    # The comment block and a scissors line with the diff below it stay in
    # the file, after the message where git's own template puts them, so
    # git's cleanup after the hook still finds and removes them.
    if comments:
        rewritten = f"{message}\n\n{comments}"
    else:
        rewritten = original.replace(original.strip(), message, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(rewritten)
    print(f"✎ fixed the commit message: {', '.join(fixed)}", file=sys.stderr)


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
    if args.ai_attribution_only or args.pr_title:
        # The text under test is what was piped, a pull request description
        # or title say. None of it is empty text: falling back to HEAD would
        # judge the last commit's message in its place.
        return stdin_content or "", None
    return stdin_content or None, None


def _reads_repository(
    args: argparse.Namespace,
    stdin_content: str | None,
    commit_file_path: str | None,
) -> bool:
    """Whether a requested check has to read the repository.

    A message that comes from a file or stdin needs no repository, and
    neither does a branch name or author piped in on stdin. Anything else
    asks git, and when git cannot read the repository each of those checks
    would come back skipped, which exits 0 as if the run had been judged.
    """
    if args.message and stdin_content is None and commit_file_path is None:
        return True
    if args.tag or args.files or args.no_force_push:
        return True
    if args.branch or args.author_name or args.author_email:
        # Beside --message, stdin is the message, so these read git.
        return args.message or stdin_content is None
    return False


def _report_unreadable_repository(reason: str) -> int:
    """Say that git cannot read the repository, and exit as a setup error."""
    print(
        "Error: git cannot read a repository here, so nothing can be checked:",
        file=sys.stderr,
    )
    print(reason, file=sys.stderr)
    return EXIT_CONFIG_ERROR


def _resolve_stdin_for_non_message(
    args: argparse.Namespace, stdin_reader: StdinReader
) -> tuple[str | None, bool]:
    """Resolve stdin content for non-message validation types.

    Returns the content, and whether it is the pre-push line rebuilt from
    pre-commit's environment rather than anything piped.
    """
    has_non_message_check = any(
        [
            args.branch,
            args.tag,
            args.files,
            args.author_name,
            args.author_email,
            args.no_force_push,
        ]
    )
    if not has_non_message_check:
        return None, False

    stdin_content = stdin_reader.read_piped_input()
    # The push-shaped checks need the pre-push ref lines. Under the
    # pre-commit framework git's native stdin is consumed, so the same data
    # is rebuilt from the PRE_COMMIT_* environment.
    if (args.no_force_push or args.files or args.tag) and stdin_content is None:
        push_input = _build_pre_commit_push_input()
        return push_input, push_input is not None
    return stdin_content, False


def _get_requested_checks(args: argparse.Namespace) -> set[str]:
    """The validation checks the CLI flags request.

    Only membership matters: rules run in catalog order, and this set is what
    the built rules are filtered against.
    """
    requested_checks: set[str] = set()

    if args.message:
        if args.ai_attribution_only:
            requested_checks |= AI_TEXT_CHECKS
        elif args.pr_title:
            requested_checks |= PR_TITLE_CHECKS
        else:
            requested_checks |= MESSAGE_CHECKS
    if args.branch:
        requested_checks |= BRANCH_CHECKS
    if args.tag:
        requested_checks.add("tag")
    if args.files:
        requested_checks |= FILES_CHECKS
    if args.author_name:
        requested_checks.add("author_name")
    if args.author_email:
        requested_checks.add("author_email")
    if args.no_force_push:
        requested_checks.add("no_force_push")

    return requested_checks


#: (flag, the checks it requests, what to say when none of them was built).
_UNCONFIGURED_HINTS = (
    (
        "files",
        ("file_size", "file_pattern", "path_length", "ai_file_pattern"),
        "--files requested but nothing is configured in the [files] section",
    ),
    (
        "branch",
        ("branch", "merge_base"),
        (
            "--branch requested but no branch rules are configured "
            "(conventional_branch = false and no require_rebase_target)"
        ),
    ),
)


def _run_json_output(
    engine: ValidationEngine,
    context: ValidationContext,
    args: argparse.Namespace,
    notices: list[dict[str, str]],
) -> int:
    """Run validation and print JSON output.

    ``notices`` lists each setting that is not in force, the lines printed on
    stderr as the config was read, so that they reach the result and not only
    the terminal.

    When a message is checked, ``ai_tools`` lists the AI tools it names (and,
    for a commit, its author), whatever the policy: what a pull request
    is labelled on.
    """
    outcomes: list[CheckOutcome] = engine.validate_all_detailed(context)
    overall = overall_status(o.status for o in outcomes)
    report: dict[str, object] = {
        "status": overall,
        "warnings": count_warnings(o.status for o in outcomes),
        "notices": notices,
        "checks": [o.to_dict() for o in outcomes],
    }
    if args.message:
        report["ai_tools"] = ai_tools_in(context, author=not context.not_a_commit)
    print(json.dumps(report, indent=2))
    # Only a failure is an error. A skipped run, or one with no checks,
    # validated nothing, but that is not a policy violation, so it must not
    # turn into a non-zero exit.
    return 1 if overall == "fail" else 0


def main() -> int:
    """The main entrypoint of commit-check program."""
    _reconfigure_io()
    parser = _get_parser()
    args = parser.parse_args()

    stdin_reader = StdinReader()

    try:
        if args.pr_title and (
            args.ai_attribution_only or args.commit_msg_file or args.rev is not None
        ):
            # Each of these names its own text to check; a title is only
            # ever piped in, and stdin cannot be two texts at once.
            parser.error(
                "--pr-title checks a title piped on stdin; it cannot be "
                "combined with --ai-attribution-only, --rev or a commit "
                "message file"
            )

        # Handle positional commit_msg_file argument for pre-commit compatibility
        if args.commit_msg_file or args.ai_attribution_only or args.pr_title:
            args.message = True

        if args.rev is not None:
            if args.commit_msg_file:
                parser.error(
                    "--rev and a commit message file both name the "
                    "thing to check; pass one or the other"
                )
            repo_error = git_repository_error()
            if repo_error:
                return _report_unreadable_repository(repo_error)
            # Fail here, with the revision named, rather than deep inside a
            # validator where the error would surface as a missing message.
            if not git_rev_parse_verify(args.rev):
                print(
                    f"Error: --rev {args.rev!r} does not resolve to a commit "
                    "in this repository",
                    file=sys.stderr,
                )
                return EXIT_CONFIG_ERROR

        # Load and merge configuration from all sources: CLI > Env > TOML > Defaults.
        # Each setting found not to be in force is printed on stderr and
        # collected here, for the JSON result.
        notices: list[dict[str, str]] = []
        config_data = ConfigMerger.from_all_sources(args, args.config, notices)

        # When --no-force-push is explicitly passed, override allow_force_push to
        # False so the rule is built even if the TOML config defaults to True.
        if args.no_force_push:
            config_data.setdefault("push", {})["allow_force_push"] = False

        # Build validation rules from config
        try:
            rule_builder = RuleBuilder(config_data, notices)
            all_rules = rule_builder.build_all_rules()
        except ConfigError as e:
            # The merged dict no longer says which file a setting came from,
            # and ``warn`` has no env or CLI form, so it was the TOML file.
            # An explicit --config is named as the user wrote it; otherwise
            # say which of the default locations was found. A setting that
            # also has a flag and a CCHK_* variable names itself, and is
            # left alone: pointing at a file it may not have come from
            # would send the reader to the wrong place.
            if e.setting:
                raise
            source = args.config or find_config_path()
            raise ConfigError(f"{source}: {e}" if source else str(e)) from e

        # Determine which checks to run
        requested_checks = _get_requested_checks(args)
        if not requested_checks:
            _print_intro(args.config)
            return 0

        # Filter rules to only include requested checks
        filtered_rules = [rule for rule in all_rules if rule.check in requested_checks]

        # Some rules exist only when configured, so a flag whose every rule
        # the config switched off would silently validate nothing — say so
        # instead of letting the quiet pass read as a verdict. (--tag always
        # builds its rule, and the author flags always build theirs.)
        built_checks = {rule.check for rule in filtered_rules}
        for requested, checks, hint in _UNCONFIGURED_HINTS:
            if getattr(args, requested) and built_checks.isdisjoint(checks):
                report_notice(notices, f"--{requested}", hint)

        engine = ValidationEngine(filtered_rules)

        # Resolve validation context inputs. With --rev the commit itself is
        # the thing under test, so stdin is never consulted: piping and a
        # revision would name two different subjects for the same checks.
        push_from_pre_commit = False
        if args.rev is not None:
            stdin_content, commit_file_path = None, None
        else:
            stdin_content, commit_file_path = _resolve_commit_message_source(
                args, stdin_reader
            )
            if not args.message:
                stdin_content, push_from_pre_commit = _resolve_stdin_for_non_message(
                    args, stdin_reader
                )

        # Next to --message, piped stdin is the message; other checks read git.
        stdin_is_message = args.message and stdin_content is not None

        if args.rev is None and _reads_repository(
            args, stdin_content, commit_file_path
        ):
            repo_error = git_repository_error()
            if repo_error:
                return _report_unreadable_repository(repo_error)

        if args.fix and not commit_file_path:
            parser.error("--fix rewrites a commit message file; pass one")
        if args.fix and commit_file_path and not args.dry_run:
            _fix_message_file(commit_file_path, filtered_rules, config_data)

        # Reset header state for this run
        print_error_header.has_been_called = False

        context = ValidationContext(
            stdin_text=stdin_content,
            commit_file=commit_file_path,
            rev=args.rev,
            config=config_data,
            no_banner=getattr(args, "no_banner", False),
            compact=getattr(args, "compact", False),
            push_upstream_fallback=args.no_force_push
            and (stdin_content is None or stdin_is_message),
            stdin_is_message=stdin_is_message,
            push_from_pre_commit=push_from_pre_commit,
            not_a_commit=args.ai_attribution_only or args.pr_title,
        )

        # Run validation – choose output mode based on --format
        output_format: str = getattr(args, "output_format", "text")
        if output_format == "json":
            exit_code = _run_json_output(engine, context, args, notices)
        else:
            result = engine.validate_all(context)
            exit_code = EXIT_PASS if result == ValidationResult.PASS else EXIT_FAIL

        if args.dry_run and exit_code == EXIT_FAIL:
            # The checks ran and their findings are printed above; only the
            # verdict is softened, so a team can preview a rule set in CI
            # without being blocked by it. Say so, or the green exit reads
            # as a pass.
            print(
                "⊘ dry run: a check failed, but --dry-run forces exit code 0",
                file=sys.stderr,
            )
            return EXIT_PASS
        return exit_code

    except (FileNotFoundError, ConfigError) as e:
        # Nothing was validated, so this is not a verdict on the commit.
        print(f"Error: {e}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    except Exception as e:  # noqa: BLE001 - last resort: report it, no traceback
        # Some exceptions carry no text (MemoryError, a bare KeyError()), and
        # "Error: " on its own says nothing; name the type instead.
        print(f"Error: {str(e) or type(e).__name__}", file=sys.stderr)
        return EXIT_FAIL


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
