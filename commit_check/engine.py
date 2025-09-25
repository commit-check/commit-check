"""Clean validation engine following SOLID principles."""

from typing import List, Optional, Dict, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum

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


class BaseValidator(ABC):
    """Abstract base validator."""

    def __init__(self, rule: ValidationRule):
        self.rule = rule

    @abstractmethod
    def validate(self, context: ValidationContext) -> ValidationResult:
        """Perform validation and return result."""
        pass

    def _should_skip_validation(self, context: ValidationContext) -> bool:
        """Determine if validation should be skipped."""
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
        if self._should_skip_validation(context):
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
        if self._should_skip_validation(context):
            return ValidationResult.PASS

        subject = self._get_subject(context)
        if not subject:
            return ValidationResult.PASS

        return self._validate_subject(subject)

    def _get_subject(self, context: ValidationContext) -> str:
        """Extract subject from commit message."""
        if context.stdin_text:
            return context.stdin_text.strip().split("\n")[0]
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

        match = re.match(r"^(?:\w+(?:\([^)]*\))?[!:]?\s*)?(\w+)", subject)
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
        if self._should_skip_validation(context):
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
        if not has_commits():
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
        if self._should_skip_validation(context):
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


class ValidationEngine:
    """Main validation engine that orchestrates all validations."""

    VALIDATOR_MAP: Dict[str, Type[BaseValidator]] = {
        "message": CommitMessageValidator,
        "subject_capitalized": SubjectCapitalizationValidator,
        "imperative": SubjectImperativeValidator,
        "subject_max_length": SubjectLengthValidator,
        "subject_min_length": SubjectLengthValidator,
        "author_name": AuthorValidator,
        "author_email": AuthorValidator,
        "allow_authors": AuthorValidator,
        "ignore_authors": AuthorValidator,
        "branch": BranchValidator,
        "merge_base": MergeBaseValidator,
        "require_signed_off_by": SignoffValidator,
        "require_body": BodyValidator,
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
