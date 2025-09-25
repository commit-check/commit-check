"""Comprehensive tests for commit_check.engine module."""

from unittest.mock import patch
from commit_check.engine import (
    ValidationResult,
    ValidationContext,
    ValidationEngine,
    CommitMessageValidator,
    SubjectCapitalizationValidator,
    SubjectImperativeValidator,
    SubjectLengthValidator,
    AuthorValidator,
    BranchValidator,
    MergeBaseValidator,
    SignoffValidator,
    BodyValidator,
    CommitTypeValidator,
)
from commit_check.rule_builder import ValidationRule


class TestValidationResult:
    def test_validation_result_values(self):
        """Test ValidationResult enum values."""
        assert ValidationResult.PASS == 0
        assert ValidationResult.FAIL == 1


class TestValidationContext:
    def test_validation_context_creation(self):
        """Test ValidationContext creation."""
        context = ValidationContext()
        assert context.stdin_text is None
        assert context.commit_file is None

        context_with_data = ValidationContext(
            stdin_text="test commit", commit_file="commit.txt"
        )
        assert context_with_data.stdin_text == "test commit"
        assert context_with_data.commit_file == "commit.txt"


class TestCommitMessageValidator:
    def test_commit_message_validator_creation(self):
        """Test CommitMessageValidator creation."""
        rule = ValidationRule(
            check="message",
            regex="^(feat|fix):",
            error="Invalid commit message",
            suggest="Use conventional format",
        )
        validator = CommitMessageValidator(rule)
        assert validator.rule == rule

    @patch("commit_check.engine.get_commit_info")
    @patch("commit_check.engine.has_commits")
    def test_commit_message_validator_with_stdin(
        self, mock_has_commits, mock_get_commit_info
    ):
        """Test CommitMessageValidator with stdin text."""
        mock_has_commits.return_value = True

        rule = ValidationRule(
            check="message",
            regex="^(feat|fix):",
            error="Invalid commit message",
            suggest="Use conventional format",
        )
        validator = CommitMessageValidator(rule)
        context = ValidationContext(stdin_text="feat: add new feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @patch("commit_check.engine.get_commit_info")
    @patch("commit_check.engine.has_commits")
    def test_commit_message_validator_failure(
        self, mock_has_commits, mock_get_commit_info
    ):
        """Test CommitMessageValidator failure case."""
        mock_has_commits.return_value = True

        rule = ValidationRule(
            check="message",
            regex="^(feat|fix):",
            error="Invalid commit message",
            suggest="Use conventional format",
        )
        validator = CommitMessageValidator(rule)
        context = ValidationContext(stdin_text="bad commit message")

        with patch.object(validator, "_print_failure") as mock_print:
            result = validator.validate(context)
            assert result == ValidationResult.FAIL
            mock_print.assert_called_once()

    @patch("commit_check.engine.has_commits")
    def test_commit_message_validator_skip_validation(self, mock_has_commits):
        """Test CommitMessageValidator skips when no commits and no stdin."""
        mock_has_commits.return_value = False

        rule = ValidationRule(
            check="message",
            regex="^(feat|fix):",
            error="Invalid commit message",
            suggest="Use conventional format",
        )
        validator = CommitMessageValidator(rule)
        context = ValidationContext()  # No stdin_text

        result = validator.validate(context)
        assert result == ValidationResult.PASS


class TestSubjectCapitalizationValidator:
    def test_subject_capitalization_pass(self):
        """Test SubjectCapitalizationValidator pass case."""
        rule = ValidationRule(
            check="subject_capitalized",
            regex="^[A-Z]",
            error="Subject must be capitalized",
            suggest="Capitalize first letter",
        )
        validator = SubjectCapitalizationValidator(rule)
        # Use conventional commit format with capitalized description
        context = ValidationContext(stdin_text="feat: Add new feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_subject_capitalization_fail(self):
        """Test SubjectCapitalizationValidator fail case."""
        rule = ValidationRule(
            check="subject_capitalized",
            regex="^[A-Z]",
            error="Subject must be capitalized",
            suggest="Capitalize first letter",
        )
        validator = SubjectCapitalizationValidator(rule)
        # Use conventional commit format with lowercase description
        context = ValidationContext(stdin_text="feat: add new feature")

        with patch.object(validator, "_print_failure") as mock_print:
            result = validator.validate(context)
            assert result == ValidationResult.FAIL
            mock_print.assert_called_once()


class TestSubjectImperativeValidator:
    def test_subject_imperative_pass(self):
        """Test SubjectImperativeValidator pass case."""
        rule = ValidationRule(
            check="imperative",
            regex="",
            error="Subject must be imperative",
            suggest="Use imperative mood",
        )
        validator = SubjectImperativeValidator(rule)
        # Use conventional commit with imperative verb "add"
        context = ValidationContext(stdin_text="feat: add new feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_subject_imperative_fail(self):
        """Test SubjectImperativeValidator fail case."""
        rule = ValidationRule(
            check="imperative",
            regex="",
            error="Subject must be imperative",
            suggest="Use imperative mood",
        )
        validator = SubjectImperativeValidator(rule)
        # Use past tense "added" which is not imperative
        context = ValidationContext(stdin_text="feat: added new feature")

        with patch.object(validator, "_print_failure") as mock_print:
            result = validator.validate(context)
            assert result == ValidationResult.FAIL
            mock_print.assert_called_once()


class TestSubjectLengthValidator:
    def test_subject_length_pass(self):
        """Test SubjectLengthValidator pass case."""
        rule = ValidationRule(
            check="subject_max_length",
            regex="",
            error="Subject too long",
            suggest="Keep subject short",
            value=50,
        )
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(stdin_text="Add feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_subject_length_fail(self):
        """Test SubjectLengthValidator fail case."""
        rule = ValidationRule(
            check="subject_max_length",
            regex="",
            error="Subject too long: max 10 characters",
            suggest="Keep subject short",
            value=10,
        )
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(stdin_text="This is a very long subject line")

        with patch.object(validator, "_print_failure") as mock_print:
            result = validator.validate(context)
            assert result == ValidationResult.FAIL
            mock_print.assert_called_once()


class TestValidationEngine:
    def test_validation_engine_creation(self):
        """Test ValidationEngine creation."""
        rules = [
            ValidationRule(
                check="message",
                regex="^(feat|fix):",
                error="Invalid commit message",
                suggest="Use conventional format",
            )
        ]
        engine = ValidationEngine(rules)
        assert engine.rules == rules

    def test_validation_engine_validator_map(self):
        """Test ValidationEngine VALIDATOR_MAP contains expected mappings."""
        engine = ValidationEngine([])

        expected_mappings = {
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
            "allow_merge_commits": CommitTypeValidator,
            "allow_revert_commits": CommitTypeValidator,
            "allow_empty_commits": CommitTypeValidator,
            "allow_fixup_commits": CommitTypeValidator,
            "allow_wip_commits": CommitTypeValidator,
        }

        for check, validator_class in expected_mappings.items():
            assert engine.VALIDATOR_MAP[check] == validator_class

    def test_validation_engine_validate_all_pass(self):
        """Test ValidationEngine validate_all with all passing rules."""
        rules = [
            ValidationRule(
                check="message",
                regex="^(feat|fix):",
                error="Invalid commit message",
                suggest="Use conventional format",
            )
        ]
        engine = ValidationEngine(rules)
        context = ValidationContext(stdin_text="feat: add new feature")

        with patch("commit_check.engine.has_commits", return_value=True):
            result = engine.validate_all(context)
            assert result == ValidationResult.PASS

    def test_validation_engine_validate_all_fail(self):
        """Test ValidationEngine validate_all with failing rule."""
        rules = [
            ValidationRule(
                check="message",
                regex="^(feat|fix):",
                error="Invalid commit message",
                suggest="Use conventional format",
            )
        ]
        engine = ValidationEngine(rules)
        context = ValidationContext(stdin_text="bad commit message")

        with patch("commit_check.engine.has_commits", return_value=True):
            result = engine.validate_all(context)
            assert result == ValidationResult.FAIL

    def test_validation_engine_unknown_validator(self):
        """Test ValidationEngine with unknown validator type."""
        rules = [
            ValidationRule(
                check="unknown_check",
                regex="",
                error="Unknown error",
                suggest="Unknown suggest",
            )
        ]
        engine = ValidationEngine(rules)
        context = ValidationContext(stdin_text="test")

        # Should skip unknown validators and continue
        result = engine.validate_all(context)
        assert result == ValidationResult.PASS
