"""Clean validation engine following SOLID principles."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from dataclasses import field

from commit_check.rule_builder import ValidationRule
from commit_check.ai_signatures import (
    detect_ai_signatures,
    find_co_authored_by_ai,
    find_assisted_by_trailers,
)
from commit_check.util import (
    fetch_remote_ref,
    fetch_upstream_ref,
    get_commit_info,
    get_git_config_value,
    get_branch_name,
    get_git_remotes,
    get_upstream_branch,
    get_upstream_remote_sha,
    has_commits,
    git_merge_base,
)
from commit_check.imperatives import IMPERATIVES


class ValidationResult(IntEnum):
    """Validation result codes."""

    PASS = 0
    FAIL = 1


@dataclass(frozen=True)
class ValidationContext:
    """Context for validation operations."""

    stdin_text: str | None = None
    commit_file: str | None = None
    config: dict = field(default_factory=dict)
    no_banner: bool = False
    compact: bool = False
    push_upstream_fallback: bool = False


@dataclass
class CheckOutcome:
    """Structured result of a single validation check.

    Returned by :meth:`ValidationEngine.validate_all_detailed` so that
    callers (e.g. ``--format json`` output, the Python API) can inspect
    individual check results without parsing human-readable terminal output.
    """

    check: str
    status: str  # "pass" or "fail"
    value: str = ""
    error: str = ""
    suggest: str = ""

    def to_dict(self) -> dict[str, str]:
        """Serialise to a plain dict (suitable for JSON encoding)."""
        return {
            "check": self.check,
            "status": self.status,
            "value": self.value,
            "error": self.error,
            "suggest": self.suggest,
        }


class BaseValidator(ABC):
    """Abstract base validator."""

    def __init__(self, rule: ValidationRule):
        self.rule = rule
        # Set to True by ValidationEngine.validate_all_detailed() to suppress
        # human-readable terminal output while still collecting failure details.
        self._suppress_output: bool = False
        # Set by ValidationEngine.validate_all() from ValidationContext flags.
        self._no_banner: bool = False
        self._compact: bool = False
        # Populated by _print_failure() on every failure, regardless of mode.
        self._last_failure: dict[str, str] | None = None

    @abstractmethod
    def validate(self, context: ValidationContext) -> ValidationResult:
        """Perform validation and return result."""
        pass

    def _should_skip_validation(self, context: ValidationContext) -> bool:
        """
        Determine if validation should be skipped.

        Skip only when there is no stdin_text, no commit_file, and no commits.
        """
        return (
            context.stdin_text is None
            and context.commit_file is None
            and not has_commits()
        )

    @staticmethod
    def _get_commit_message(context: ValidationContext) -> str:
        """Get commit message from context or git."""
        if context.stdin_text:
            return context.stdin_text.strip()

        if context.commit_file:
            try:
                with open(context.commit_file, "r") as f:
                    return f.read().strip()
            except FileNotFoundError:
                pass

        # Fallback to git log
        subject = get_commit_info("s")
        body = get_commit_info("b")
        return f"{subject}\n\n{body}".strip()

    def _author_in_ignore_list(self, context: ValidationContext) -> bool:
        """Check if the current author or any co-author is in the ignore list."""
        import re

        ignore_authors = context.config.get("commit", {}).get("ignore_authors", [])
        if not ignore_authors:
            return False

        current_author = get_commit_info("an")
        if current_author and current_author in ignore_authors:
            return True

        # Check co-authors from the commit message body
        message = self._get_commit_body(context)
        if not message:
            return False

        co_authors = re.findall(
            r"^Co-authored-by:\s*([^<\n]+)\s*(?:<|$)",
            message,
            re.MULTILINE,
        )
        return any(co_author.strip() in ignore_authors for co_author in co_authors)

    @staticmethod
    def _get_commit_body(context: ValidationContext) -> str:
        """Retrieve the commit message body from context or git."""
        if context.stdin_text:
            return context.stdin_text
        if context.commit_file:
            try:
                with open(context.commit_file, "r") as f:
                    return f.read()
            except (OSError, IOError):
                pass
        return get_commit_info("b")

    def _should_skip_commit_validation(self, context: ValidationContext) -> bool:
        """
        Determine if commit validation should be skipped.

        Skip if the current author or any co-author is in the ignore_authors list
        for commits, or if no stdin_text, no commit_file, and no commits exist.
        """
        if self._author_in_ignore_list(context):
            return True

        return (
            context.stdin_text is None
            and context.commit_file is None
            and not has_commits()
        )

    def _should_skip_branch_validation(self, context: ValidationContext) -> bool:
        """
        Determine if branch validation should be skipped.

        Skip if the current author is in the ignore_authors list for branches,
        or if no stdin_text and no commits exist.
        """
        ignore_authors = context.config.get("branch", {}).get("ignore_authors", [])
        current_author = get_commit_info("an")
        if current_author and current_author in ignore_authors:
            return True
        return context.stdin_text is None and not has_commits()

    def _print_failure(self, actual_value: str, regex_or_constraint: str = "") -> None:
        """Record and (unless suppressed) print a standardised failure message."""
        rule_dict = self.rule.to_dict()

        # Always store structured failure details for programmatic consumers.
        self._last_failure = {
            "check": self.rule.check,
            "value": actual_value,
            "error": self.rule.error or "",
            "suggest": self.rule.suggest or "",
        }

        if not self._suppress_output:
            from commit_check.util import _print_failure

            _print_failure(
                rule_dict,
                actual_value,
                no_banner=self._no_banner,
                compact=self._compact,
            )


class CommitMessageValidator(BaseValidator):
    """Validates commit messages against conventional commit standards."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_commit_validation(context):
            return ValidationResult.PASS

        message = self._get_commit_message(context)
        if not message:
            return ValidationResult.PASS

        import re

        if self.rule.regex and re.match(self.rule.regex, message):
            return ValidationResult.PASS

        self._print_failure(message)
        return ValidationResult.FAIL


class SubjectValidator(BaseValidator):
    """Validates commit subject lines."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_commit_validation(context):
            return ValidationResult.PASS

        subject = self._get_subject(context)
        if not subject:
            return ValidationResult.PASS

        return self._validate_subject(subject)

    def _get_subject(self, context: ValidationContext) -> str:
        """Extract subject from commit message."""
        if context.stdin_text:
            return context.stdin_text.strip().split("\n")[0]

        if context.commit_file:
            try:
                with open(context.commit_file, "r") as f:
                    message = f.read().strip()
                    return message.split("\n")[0]
            except FileNotFoundError:
                pass

        return get_commit_info("s")

    def _validate_subject(self, _subject: str) -> ValidationResult:
        """Override in subclasses for specific validation logic."""
        return ValidationResult.PASS


class SubjectCapitalizationValidator(SubjectValidator):
    """Validates that subject starts with capital letter."""

    def _validate_subject(self, subject: str) -> ValidationResult:
        # Skip merge commits
        if subject.lower().startswith("merge"):
            return ValidationResult.PASS

        # For conventional commits, check the description part after the colon
        import re

        match = re.match(r"^(?:\w+(?:\([^)]*\))?[!:]?\s*)(.*)", subject)
        if match:
            description = match.group(1).strip()
            if description and description[0].isupper():
                return ValidationResult.PASS
        else:
            # For non-conventional commits, check the first character
            if subject and subject[0].isupper():
                return ValidationResult.PASS

        self._print_failure(subject)
        return ValidationResult.FAIL


class SubjectImperativeValidator(SubjectValidator):
    """Validates that subject uses imperative mood."""

    def _validate_subject(self, subject: str) -> ValidationResult:
        # Skip merge commits and fixup commits
        if subject.lower().startswith(("merge", "fixup!")):
            return ValidationResult.PASS

        # Extract first word (ignore conventional commit prefixes)
        import re

        # support breaking changes (feat!:)
        match = re.match(r"^(?:\w+(?:\([^)]*\))?!?:\s*)?(\w+)", subject)
        if not match:
            return ValidationResult.PASS

        first_word = match.group(1).lower()
        if first_word in IMPERATIVES:
            return ValidationResult.PASS

        self._print_failure(subject)
        return ValidationResult.FAIL


class SubjectLengthValidator(SubjectValidator):
    """Validates subject line length constraints."""

    def _validate_subject(self, subject: str) -> ValidationResult:
        # Skip merge commits for length checks
        if subject.lower().startswith("merge"):
            return ValidationResult.PASS

        length = len(subject)
        constraint_value = self.rule.value

        if (
            (self.rule.check == "subject_max_length" and length <= constraint_value)
            or (self.rule.check == "subject_min_length" and length >= constraint_value)
            or self.rule.check not in ["subject_max_length", "subject_min_length"]
        ):
            return ValidationResult.PASS

        self._print_failure(subject, f"length={length}, constraint={constraint_value}")
        return ValidationResult.FAIL


class AuthorValidator(BaseValidator):
    """Validates author information."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        # Use commit skip logic for ignore_authors
        if self._should_skip_commit_validation(context):
            return ValidationResult.PASS

        author_value = self._get_author_value(context)
        if not author_value:
            return ValidationResult.PASS

        return self._validate_author(author_value)

    def _get_author_value(self, context: ValidationContext) -> str:
        """Get author value based on rule type.

        Checks git config first (for pre-commit validation of the configured identity),
        then falls back to the last commit's author info.
        """
        if context.stdin_text:
            return context.stdin_text.strip()

        git_config_map = {
            "author_name": "user.name",
            "author_email": "user.email",
        }
        git_log_map = {
            "author_name": "an",
            "author_email": "ae",
        }

        # Try git config first (validates configured identity for new commits)
        config_key = git_config_map.get(self.rule.check, "")
        if config_key:
            config_value = get_git_config_value(config_key)
            if config_value:
                return config_value

        # Fall back to last commit's author info
        format_str = git_log_map.get(self.rule.check, "")
        return get_commit_info(format_str) if format_str else ""

    def _validate_author(self, author_value: str) -> ValidationResult:
        """Validate author against rule constraints."""
        if self.rule.regex:
            import re

            if re.match(self.rule.regex, author_value):
                return ValidationResult.PASS
            self._print_failure(author_value)
            return ValidationResult.FAIL

        if self.rule.allowed and author_value not in self.rule.allowed:
            self._print_failure(author_value, f"allowed={sorted(self.rule.allowed)}")
            return ValidationResult.FAIL

        if self.rule.ignored and author_value in self.rule.ignored:
            return ValidationResult.PASS  # Ignored authors pass silently

        return ValidationResult.PASS


class BranchValidator(BaseValidator):
    """Validates branch names."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_branch_validation(context):
            return ValidationResult.PASS
        branch_name = (
            context.stdin_text.strip() if context.stdin_text else get_branch_name()
        )

        if not self.rule.regex:
            return ValidationResult.PASS

        import re

        if re.match(self.rule.regex, branch_name):
            return ValidationResult.PASS

        self._print_failure(branch_name)
        return ValidationResult.FAIL


class MergeBaseValidator(BaseValidator):
    """Validates merge base ancestry."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_branch_validation(context):
            return ValidationResult.PASS

        current_branch = get_branch_name()
        target_pattern = self.rule.regex

        if not target_pattern:
            return ValidationResult.PASS

        # Find target branch matching the pattern
        target_branch = self._find_target_branch(target_pattern)
        if not target_branch:
            return ValidationResult.PASS

        result = git_merge_base(target_branch, current_branch)
        if result == 0:
            return ValidationResult.PASS

        self._print_failure(current_branch, f"target={target_branch}")
        return ValidationResult.FAIL

    def _find_target_branch(self, pattern: str) -> str | None:
        """Find target branch by verifying refs directly.

        Uses ``git rev-parse --verify`` for exact ref resolution instead of
        scanning ``git branch -a`` output with a regex. Strips common regex
        anchors (``^``, ``$``) from the pattern to obtain a branch name,
        then attempts to verify it as a local ref first, falling back to
        the remote tracking ref under ``origin/``.

        :param pattern: The raw regex pattern from the rule config (e.g.
            ``"^main$"`` or ``"main"``).
        :returns: The resolved branch name if verified, ``None`` otherwise.
        """
        import subprocess

        # Strip common regex anchors to obtain a clean branch name
        branch_name = pattern.lstrip("^").rstrip("$").strip()
        if not branch_name:
            return None

        # Try local branch first (refs/heads/ avoids ambiguity with tags)
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", f"refs/heads/{branch_name}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return branch_name
        except subprocess.CalledProcessError:
            pass

        # Try remote tracking branch under origin/
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch_name}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return branch_name
        except subprocess.CalledProcessError:
            pass

        return None


class SignoffValidator(BaseValidator):
    """Validates that commit messages contain required signoff trailer."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_validation(context):
            return ValidationResult.PASS

        message = self._get_commit_message(context)
        if not message:
            return ValidationResult.PASS

        import re

        if self.rule.regex and re.search(self.rule.regex, message):
            return ValidationResult.PASS

        self._print_failure(message)
        return ValidationResult.FAIL


class BodyValidator(BaseValidator):
    """Validates that commit messages contain a body when required."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_commit_validation(context):
            return ValidationResult.PASS

        message = self._get_commit_message(context)
        if not message:
            return ValidationResult.PASS

        # Split message into lines and check if there's content after the subject
        lines = message.strip().split("\n")

        # Filter out empty lines
        non_empty_lines = [line.strip() for line in lines if line.strip()]

        # If there's more than just the subject line, we have a body
        if len(non_empty_lines) > 1:
            return ValidationResult.PASS

        # Check if there's content after the first line (even if separated by empty lines)
        if len(lines) > 1:
            body_content = "\n".join(lines[1:]).strip()
            if body_content:
                return ValidationResult.PASS

        self._print_failure(message)
        return ValidationResult.FAIL


class ForcePushValidator(BaseValidator):
    """Validates that no force push is being performed.

    Reads pushed ref information from stdin (provided by git's pre-push hook)
    in the format::

        <local ref> <local sha1> <remote ref> <remote sha1>

    A force push is detected when the remote SHA is not an ancestor of the
    local SHA, meaning local history would overwrite the remote.
    """

    ZERO_SHA = "0000000000000000000000000000000000000000"

    def validate(self, context: ValidationContext) -> ValidationResult:
        if not context.stdin_text:
            if context.push_upstream_fallback:
                return self._check_current_branch_against_upstream()
            return ValidationResult.PASS

        for line in context.stdin_text.splitlines():
            result = self._check_push_line(line.strip())
            if result == ValidationResult.FAIL:
                return ValidationResult.FAIL

        return ValidationResult.PASS

    def _check_current_branch_against_upstream(self) -> ValidationResult:
        """Check whether pushing HEAD to its upstream would require force."""
        upstream_ref = get_upstream_branch()
        if not upstream_ref:
            return ValidationResult.PASS

        target_ref = get_upstream_remote_sha(upstream_ref) or upstream_ref
        returncode = git_merge_base(target_ref, "HEAD")
        if (
            returncode == 128
            and target_ref != upstream_ref
            and fetch_upstream_ref(upstream_ref)
        ):
            returncode = git_merge_base(target_ref, "HEAD")
        if returncode == 1:
            self._print_failure(f"{get_branch_name()} -> {upstream_ref}")
            return ValidationResult.FAIL

        return ValidationResult.PASS

    def _check_push_line(self, line: str) -> ValidationResult:
        """Check a single pushed ref line for force push."""
        if not line:
            return ValidationResult.PASS

        parts = line.split()
        if len(parts) < 4:
            return ValidationResult.PASS

        local_ref, local_sha, remote_ref, remote_sha = (
            parts[0],
            parts[1],
            parts[2],
            parts[3],
        )

        # Zero SHA for remote means a new branch push (not a force push)
        if remote_sha == self.ZERO_SHA:
            return ValidationResult.PASS

        # Check if the remote SHA is an ancestor of the local SHA.
        # returncode 0  -> remote is ancestor of local (fast-forward push, OK)
        # returncode 1  -> not an ancestor (force push detected)
        # returncode 128 -> SHA may be unknown locally; fetch remote ref and retry
        returncode = git_merge_base(remote_sha, local_sha)
        if returncode == 128:
            for remote in self._remote_candidates_for_push(remote_ref):
                if not fetch_remote_ref(remote, remote_ref):
                    continue
                returncode = git_merge_base(remote_sha, local_sha)
                if returncode != 128:
                    break
        if returncode == 1:
            self._print_failure(f"{local_ref} -> {remote_ref}")
            return ValidationResult.FAIL

        return ValidationResult.PASS

    def _remote_candidates_for_push(self, remote_ref: str) -> list[str]:
        """Return remotes worth fetching for a pushed branch ref."""
        if not remote_ref.startswith("refs/heads/"):
            return []

        remotes: list[str] = []
        upstream_ref = get_upstream_branch()
        upstream_parts = upstream_ref.split("/", 1)
        remote_branch = remote_ref.removeprefix("refs/heads/")
        if len(upstream_parts) == 2 and upstream_parts[1] == remote_branch:
            remotes.append(upstream_parts[0])

        remotes.extend(remote for remote in get_git_remotes() if remote not in remotes)
        return remotes


class CommitTypeValidator(BaseValidator):
    """Base validator for special commit types (merge, revert, fixup, WIP, empty)."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_commit_validation(context):
            return ValidationResult.PASS

        message = self._get_commit_message(context)
        if not message:
            return ValidationResult.PASS

        # Check if this commit type is allowed based on rule configuration
        is_allowed = self._is_commit_type_allowed(message)

        if not is_allowed:
            self._print_failure(message)
            return ValidationResult.FAIL

        return ValidationResult.PASS

    def _is_commit_type_allowed(self, message: str) -> bool:
        """Check if the commit type is allowed based on the rule check."""
        check = self.rule.check

        if check == "allow_merge_commits":
            return self._is_merge_commit_allowed(message)
        elif check == "allow_revert_commits":
            return self._is_revert_commit_allowed(message)
        elif check == "allow_empty_commits":
            return self._is_empty_commit_allowed(message)
        elif check == "allow_fixup_commits":
            return self._is_fixup_commit_allowed(message)
        elif check == "allow_wip_commits":
            return self._is_wip_commit_allowed(message)

        return True

    def _is_merge_commit_allowed(self, message: str) -> bool:
        """Check if merge commits are allowed."""
        is_merge = message.startswith("Merge ")
        # If rule value is True, allow merge commits. If False, reject them.
        return not is_merge or self.rule.value

    def _is_revert_commit_allowed(self, message: str) -> bool:
        """Check if revert commits are allowed."""
        is_revert = message.lower().startswith("revert ")
        return not is_revert or self.rule.value

    def _is_empty_commit_allowed(self, message: str) -> bool:
        """Check if empty commits are allowed."""
        is_empty = not message.strip()
        return not is_empty or self.rule.value

    def _is_fixup_commit_allowed(self, message: str) -> bool:
        """Check if fixup commits are allowed."""
        is_fixup = message.startswith("fixup!")
        return not is_fixup or self.rule.value

    def _is_wip_commit_allowed(self, message: str) -> bool:
        """Check if WIP commits are allowed."""
        upper_msg = message.upper()
        is_wip = (
            upper_msg.startswith("WIP:")  # wip: / WIP:
            or upper_msg.startswith("[WIP]")  # [wip] / [WIP]
            or upper_msg.startswith("WIP ")  # WIP at start with space
            or upper_msg == "WIP"  # exact WIP
        )
        return not is_wip or self.rule.value


class AiAttributionValidator(BaseValidator):
    """Validates commit messages against AI attribution policy.

    Three modes (configured via ``[commit] ai_attribution``):

    * ``forbid`` — Reject any commit that contains known AI tool signatures.
    * ``require`` — If AI signatures are present, they MUST use the configured
      trailer style (``ai_trailer_style``).  Pure pass-through commits (no
      signatures) are allowed.
    * ``ignore`` — No validation (default).
    """

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_commit_validation(context):
            return ValidationResult.PASS

        message = self._get_commit_body(context)
        if not message:
            return ValidationResult.PASS

        policy = self.rule.value  # "ignore" | "require" | "forbid"
        if policy == "ignore":
            return ValidationResult.PASS

        signatures = detect_ai_signatures(message)

        if policy == "forbid":
            if signatures:
                tools = {s["tool"] for s in signatures}
                self._record_failure(
                    value=", ".join(sorted(tools)),
                    error=f"AI-assisted commit is forbidden — detected tools: {', '.join(sorted(tools))}",
                    suggest="Remove AI-generated trailers from the commit message",
                )
                return ValidationResult.FAIL
            return ValidationResult.PASS

        if policy == "require":
            if not signatures:
                # Cannot detect undisclosed AI usage; pass through.
                return ValidationResult.PASS

            # AI signatures found — check that they use the required style.
            trailer_style = self.rule.allowed or ["assisted-by"]
            preferred = trailer_style[0] if trailer_style else "assisted-by"

            if preferred == "assisted-by":
                co_ai = find_co_authored_by_ai(message)
                if co_ai:
                    self._record_failure(
                        value="; ".join(co_ai),
                        error="AI attribution style violation: project requires 'Assisted-by:' trailer (Linux kernel style)",
                        suggest="Replace 'Co-authored-by: <AI>' with 'Assisted-by: <tool>:<model>'",
                    )
                    return ValidationResult.FAIL
            elif preferred == "co-authored-by":
                assisted = find_assisted_by_trailers(message)
                if assisted:
                    self._record_failure(
                        value="; ".join(assisted),
                        error="AI attribution style violation: project requires 'Co-authored-by:' trailer",
                        suggest="Replace 'Assisted-by: <tool>:<model>' with 'Co-authored-by: <AI> <email>'",
                    )
                    return ValidationResult.FAIL

            return ValidationResult.PASS

        return ValidationResult.PASS

    def _record_failure(self, value: str, error: str, suggest: str) -> None:
        """Record a failure with dynamic error/suggest messages."""
        self._last_failure = {
            "check": self.rule.check,
            "value": value,
            "error": error,
            "suggest": suggest,
        }
        if not self._suppress_output:
            rule_dict = self.rule.to_dict()
            from commit_check.util import _print_failure

            _print_failure(
                rule_dict,
                value,
                no_banner=self._no_banner,
                compact=self._compact,
            )


class AiTrailerStyleValidator(BaseValidator):
    """Validates that AI-related trailers use the project-preferred style.

    This validator is a companion to ``ai_attribution = "require"``.  It checks
    that any known AI trailers use the format specified by ``ai_trailer_style``
    in the config (``"assisted-by"`` or ``"co-authored-by"``).

    When the preferred style is ``"assisted-by"``:
    * ``Co-authored-by: Claude`` → FAIL (should be ``Assisted-by: Claude:...``)

    When the preferred style is ``"co-authored-by"``:
    * ``Assisted-by: Claude:claude-sonnet`` → FAIL
    """

    def validate(self, context: ValidationContext) -> ValidationResult:
        if self._should_skip_commit_validation(context):
            return ValidationResult.PASS

        message = self._get_commit_body(context)
        if not message:
            return ValidationResult.PASS

        preferred = self.rule.value  # "assisted-by" or "co-authored-by"
        signatures = detect_ai_signatures(message)

        if not signatures:
            return ValidationResult.PASS

        if preferred == "assisted-by":
            co_ai = find_co_authored_by_ai(message)
            if co_ai:
                self._record_failure(
                    value="; ".join(co_ai),
                    error="AI trailer style violation: project requires 'Assisted-by:' trailer",
                    suggest="Replace 'Co-authored-by: <AI>' with 'Assisted-by: <tool>:<model>'",
                )
                return ValidationResult.FAIL

        elif preferred == "co-authored-by":
            assisted = find_assisted_by_trailers(message)
            if assisted:
                self._record_failure(
                    value="; ".join(assisted),
                    error="AI trailer style violation: project requires 'Co-authored-by:' trailer",
                    suggest="Replace 'Assisted-by: <tool>:<model>' with 'Co-authored-by: <AI> <email>'",
                )
                return ValidationResult.FAIL

        return ValidationResult.PASS

    def _record_failure(self, value: str, error: str, suggest: str) -> None:
        """Record a failure with dynamic error/suggest messages."""
        self._last_failure = {
            "check": self.rule.check,
            "value": value,
            "error": error,
            "suggest": suggest,
        }
        if not self._suppress_output:
            rule_dict = self.rule.to_dict()
            from commit_check.util import _print_failure

            _print_failure(
                rule_dict,
                value,
                no_banner=self._no_banner,
                compact=self._compact,
            )


class ValidationEngine:
    """Main validation engine that orchestrates all validations."""

    VALIDATOR_MAP: dict[str, type[BaseValidator]] = {
        "message": CommitMessageValidator,
        "subject_capitalized": SubjectCapitalizationValidator,
        "subject_imperative": SubjectImperativeValidator,
        "subject_max_length": SubjectLengthValidator,
        "subject_min_length": SubjectLengthValidator,
        "author_name": AuthorValidator,
        "author_email": AuthorValidator,
        "branch": BranchValidator,
        "merge_base": MergeBaseValidator,
        "require_signed_off_by": SignoffValidator,
        "require_body": BodyValidator,
        "allow_merge_commits": CommitTypeValidator,
        "allow_revert_commits": CommitTypeValidator,
        "allow_empty_commits": CommitTypeValidator,
        "allow_fixup_commits": CommitTypeValidator,
        "allow_wip_commits": CommitTypeValidator,
        "ignore_authors": CommitTypeValidator,
        "no_force_push": ForcePushValidator,
        "ai_attribution": AiAttributionValidator,
        "ai_trailer_style": AiTrailerStyleValidator,
    }

    def __init__(self, rules: list[ValidationRule]):
        self.rules = rules

    def validate_all(self, context: ValidationContext) -> ValidationResult:
        """Run all validations and return overall result."""
        results = []

        for rule in self.rules:
            validator_class = self.VALIDATOR_MAP.get(rule.check)
            if not validator_class:
                continue  # Skip unknown validators

            validator: BaseValidator = validator_class(rule)
            validator._no_banner = context.no_banner
            validator._compact = context.compact
            result = validator.validate(context)
            results.append(result)

        # Return FAIL if any validation failed
        return (
            ValidationResult.FAIL
            if ValidationResult.FAIL in results
            else ValidationResult.PASS
        )

    def validate_all_detailed(self, context: ValidationContext) -> list[CheckOutcome]:
        """Run all validations and return structured :class:`CheckOutcome` objects.

        Unlike :meth:`validate_all`, this method:

        * **Suppresses** all human-readable terminal output (ASCII art, colour).
        * Returns one :class:`CheckOutcome` per rule so callers can inspect or
          serialise individual check results (e.g. as JSON for AI agents).

        Example::

            engine = ValidationEngine(rules)
            outcomes = engine.validate_all_detailed(context)
            failed = [o for o in outcomes if o.status == "fail"]
        """
        outcomes: list[CheckOutcome] = []

        for rule in self.rules:
            validator_class = self.VALIDATOR_MAP.get(rule.check)
            if not validator_class:
                continue

            validator: BaseValidator = validator_class(rule)
            validator._suppress_output = True  # collect, don't print
            result = validator.validate(context)

            if result == ValidationResult.FAIL:
                failure = validator._last_failure or {}
                outcomes.append(
                    CheckOutcome(
                        check=rule.check,
                        status="fail",
                        value=failure.get("value", ""),
                        error=failure.get("error", ""),
                        suggest=failure.get("suggest", ""),
                    )
                )
            else:
                outcomes.append(CheckOutcome(check=rule.check, status="pass"))

        return outcomes
