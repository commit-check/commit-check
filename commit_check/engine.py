"""Clean validation engine following SOLID principles."""

from typing import List, Optional, Dict, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from dataclasses import field

from commit_check.rule_builder import ValidationRule
from commit_check.util import (
    get_commit_info,
    get_branch_name,
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

    stdin_text: Optional[str] = None
    commit_file: Optional[str] = None
    config: Dict = field(default_factory=dict)


class BaseValidator(ABC):
    """Abstract base validator."""

    def __init__(self, rule: ValidationRule):
        self.rule = rule

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

    def _should_skip_commit_validation(self, context: ValidationContext) -> bool:
        """
        Determine if commit validation should be skipped.

        Skip if the current author is in the ignore_authors list for commits,
        or if no stdin_text, no commit_file, and no commits exist.
        """
        ignore_authors = context.config.get("commit", {}).get("ignore_authors", [])
        current_author = get_commit_info("an")
        if current_author and current_author in ignore_authors:
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
        """Print standardized failure message."""
        from commit_check.util import _print_failure

        rule_dict = self.rule.to_dict()
        constraint = regex_or_constraint or rule_dict.get("regex", "")
        _print_failure(rule_dict, constraint, actual_value)


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

    def _get_commit_message(self, context: ValidationContext) -> str:
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

    def _validate_subject(self, subject: str) -> ValidationResult:
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

        if self.rule.check == "subject_max_length" and length <= constraint_value:
            return ValidationResult.PASS
        elif self.rule.check == "subject_min_length" and length >= constraint_value:
            return ValidationResult.PASS
        elif self.rule.check not in ["subject_max_length", "subject_min_length"]:
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
        """Get author value based on rule type."""
        if context.stdin_text:
            return context.stdin_text.strip()

        format_map = {
            "author_name": "an",
            "author_email": "ae",
        }
        format_str = format_map.get(self.rule.check, "")
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

    def _find_target_branch(self, pattern: str) -> Optional[str]:
        """Find target branch matching the pattern."""
        import subprocess
        import re

        try:
            all_branches = subprocess.check_output(
                ["git", "branch", "-a"], encoding="utf-8"
            ).splitlines()

            for branch in all_branches:
                clean_branch = (
                    branch.strip().replace("* ", "").replace("remotes/origin/", "")
                )
                if re.match(pattern, clean_branch):
                    return clean_branch
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

    def _get_commit_message(self, context: ValidationContext) -> str:
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

    def _get_commit_message(self, context: ValidationContext) -> str:
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
        is_wip = message.upper().startswith("WIP:")
        return not is_wip or self.rule.value

    def _get_commit_message(self, context: ValidationContext) -> str:
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


class ValidationEngine:
    """Main validation engine that orchestrates all validations."""

    VALIDATOR_MAP: Dict[str, Type[BaseValidator]] = {
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
    }

    def __init__(self, rules: List[ValidationRule]):
        self.rules = rules

    def validate_all(self, context: ValidationContext) -> ValidationResult:
        """Run all validations and return overall result."""
        results = []

        for rule in self.rules:
            validator_class = self.VALIDATOR_MAP.get(rule.check)
            if not validator_class:
                continue  # Skip unknown validators

            validator: BaseValidator = validator_class(rule)
            result = validator.validate(context)
            results.append(result)

        # Return FAIL if any validation failed
        return (
            ValidationResult.FAIL
            if ValidationResult.FAIL in results
            else ValidationResult.PASS
        )
