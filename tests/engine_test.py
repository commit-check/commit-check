"""Tests for commit_check.engine module."""

import pytest
import tempfile
import os
from unittest.mock import patch
from commit_check.engine import (
    ValidationResult,
    ValidationContext,
    BaseValidator,
    ValidationEngine,
    CommitMessageValidator,
    BranchValidator,
    AuthorValidator,
    CommitTypeValidator,
    SubjectImperativeValidator,
    SubjectLengthValidator,
    SignoffValidator,
    SubjectCapitalizationValidator,
    BodyValidator,
    MergeBaseValidator,
)
from commit_check.rule_builder import ValidationRule


class TestValidationResult:
    def test_validation_result_enum(self):
        """Test ValidationResult enum values."""
        assert ValidationResult.PASS.value == 0
        assert ValidationResult.FAIL.value == 1


class TestValidationContext:
    def test_validation_context_creation(self):
        """Test ValidationContext creation and properties."""
        context = ValidationContext(
            stdin_text="test message", commit_file="/path/to/commit"
        )
        assert context.stdin_text == "test message"
        assert context.commit_file == "/path/to/commit"

    def test_validation_context_defaults(self):
        """Test ValidationContext with default values."""
        context = ValidationContext()
        assert context.stdin_text is None
        assert context.commit_file is None


class TestBaseValidator:
    def test_base_validator_is_abstract(self):
        """Test that BaseValidator cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseValidator()


class TestCommitMessageValidator:
    def test_commit_message_validator_valid_conventional_commit(self):
        """Test CommitMessageValidator with valid conventional commit."""
        rule = ValidationRule(
            check="message",
            pattern=r"^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .+",
        )
        validator = CommitMessageValidator(rule)
        context = ValidationContext(stdin_text="feat: add new feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_commit_message_validator_invalid_commit(self):
        """Test CommitMessageValidator with invalid commit message."""
        rule = ValidationRule(
            check="message",
            pattern=r"^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .+",
        )
        validator = CommitMessageValidator(rule)
        context = ValidationContext(stdin_text="invalid commit message")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    def test_commit_message_validator_with_file(self):
        """Test CommitMessageValidator reading from file."""
        rule = ValidationRule(check="message", pattern=r"^(feat|fix):")
        validator = CommitMessageValidator(rule)

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("fix: resolve issue")
            f.flush()

            try:
                context = ValidationContext(commit_file=f.name)
                result = validator.validate(context)
                assert result == ValidationResult.PASS
            finally:
                os.unlink(f.name)

    def test_commit_message_validator_file_not_found(self):
        """Test CommitMessageValidator with non-existent file."""
        rule = ValidationRule(check="message", pattern=r"^feat:")
        validator = CommitMessageValidator(rule)
        context = ValidationContext(commit_file="/nonexistent/file")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @patch("commit_check.util.get_commit_info")
    def test_commit_message_validator_from_git(self, mock_get_commit_info):
        """Test CommitMessageValidator reading from git."""
        mock_get_commit_info.return_value = "feat: add feature from git"

        rule = ValidationRule(check="message", pattern=r"^feat:")
        validator = CommitMessageValidator(rule)
        context = ValidationContext()

        result = validator.validate(context)
        assert result == ValidationResult.PASS
        mock_get_commit_info.assert_called_once_with("s")


class TestBranchValidator:
    @patch("commit_check.util.get_branch_name")
    def test_branch_validator_valid_branch(self, mock_get_branch_name):
        """Test BranchValidator with valid branch name."""
        mock_get_branch_name.return_value = "feature/new-feature"

        rule = ValidationRule(check="branch", pattern=r"^(feature|bugfix|hotfix)/.+")
        validator = BranchValidator(rule)
        context = ValidationContext()

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @patch("commit_check.util.get_branch_name")
    def test_branch_validator_invalid_branch(self, mock_get_branch_name):
        """Test BranchValidator with invalid branch name."""
        mock_get_branch_name.return_value = "invalid-branch-name"

        rule = ValidationRule(check="branch", pattern=r"^(feature|bugfix|hotfix)/.+")
        validator = BranchValidator(rule)
        context = ValidationContext()

        result = validator.validate(context)
        assert result == ValidationResult.FAIL


class TestAuthorValidator:
    @patch("commit_check.util.get_commit_info")
    def test_author_validator_name_valid(self, mock_get_commit_info):
        """Test AuthorValidator for author name."""
        mock_get_commit_info.return_value = "John Doe"

        rule = ValidationRule(check="author_name", pattern=r"^[A-Z][a-z]+ [A-Z][a-z]+$")
        validator = AuthorValidator(rule)
        context = ValidationContext()

        result = validator.validate(context)
        assert result == ValidationResult.PASS
        mock_get_commit_info.assert_called_once_with("an")

    @patch("commit_check.util.get_commit_info")
    def test_author_validator_email_valid(self, mock_get_commit_info):
        """Test AuthorValidator for author email."""
        mock_get_commit_info.return_value = "john.doe@example.com"

        rule = ValidationRule(
            check="author_email",
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        )
        validator = AuthorValidator(rule)
        context = ValidationContext()

        result = validator.validate(context)
        assert result == ValidationResult.PASS
        mock_get_commit_info.assert_called_once_with("ae")


class TestCommitTypeValidator:
    def test_commit_type_validator_merge_commits(self):
        """Test CommitTypeValidator with merge commits."""
        rule = ValidationRule(check="allow_merge_commits", allow=True)
        validator = CommitTypeValidator(rule)
        context = ValidationContext(stdin_text="Merge branch 'feature' into main")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_commit_type_validator_revert_commits(self):
        """Test CommitTypeValidator with revert commits."""
        rule = ValidationRule(check="allow_revert_commits", allow=True)
        validator = CommitTypeValidator(rule)
        context = ValidationContext(stdin_text='Revert "feat: add feature"')

        result = validator.validate(context)
        assert result == ValidationResult.PASS


class TestSubjectImperativeValidator:
    def test_imperative_validator_valid_imperative(self):
        """Test SubjectImperativeValidator with valid imperative mood."""
        rule = ValidationRule(check="imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text="feat: add new feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_imperative_validator_invalid_imperative(self):
        """Test SubjectImperativeValidator with non-imperative mood."""
        rule = ValidationRule(check="imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text="feat: added new feature")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL


class TestSubjectLengthValidator:
    def test_subject_length_validator_max_valid(self):
        """Test SubjectLengthValidator with valid max length."""
        rule = ValidationRule(check="subject_max_length", length=50)
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(stdin_text="feat: short message")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_subject_length_validator_max_too_long(self):
        """Test SubjectLengthValidator with message too long."""
        rule = ValidationRule(check="subject_max_length", length=20)
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(
            stdin_text="feat: this is a very long commit message that exceeds the limit"
        )

        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    def test_subject_length_validator_min_valid(self):
        """Test SubjectLengthValidator with valid min length."""
        rule = ValidationRule(check="subject_min_length", length=10)
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_subject_length_validator_min_too_short(self):
        """Test SubjectLengthValidator with message too short."""
        rule = ValidationRule(check="subject_min_length", length=20)
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(stdin_text="feat: fix")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL


class TestSignoffValidator:
    def test_signoff_validator_valid(self):
        """Test SignoffValidator with valid signoff."""
        rule = ValidationRule(check="require_signed_off_by")
        validator = SignoffValidator(rule)
        context = ValidationContext(
            stdin_text="feat: add feature\n\nSigned-off-by: John Doe <john@example.com>"
        )

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_signoff_validator_missing_signoff(self):
        """Test SignoffValidator with missing signoff."""
        rule = ValidationRule(check="require_signed_off_by")
        validator = SignoffValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL


class TestSubjectCapitalizationValidator:
    def test_subject_capitalization_validator_valid(self):
        """Test SubjectCapitalizationValidator with capitalized subject."""
        rule = ValidationRule(check="subject_capitalized")
        validator = SubjectCapitalizationValidator(rule)
        context = ValidationContext(stdin_text="feat: Add new feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_subject_capitalization_validator_not_capitalized(self):
        """Test SubjectCapitalizationValidator with non-capitalized subject."""
        rule = ValidationRule(check="subject_capitalized")
        validator = SubjectCapitalizationValidator(rule)
        context = ValidationContext(stdin_text="feat: add new feature")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL


class TestBodyValidator:
    def test_body_validator_with_body(self):
        """Test BodyValidator with commit body."""
        rule = ValidationRule(check="require_body")
        validator = BodyValidator(rule)
        context = ValidationContext(
            stdin_text="feat: add feature\n\nThis is the commit body"
        )

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_body_validator_no_body(self):
        """Test BodyValidator without commit body."""
        rule = ValidationRule(check="require_body")
        validator = BodyValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL


class TestMergeBaseValidator:
    @patch("commit_check.util.git_merge_base")
    def test_merge_base_validator_valid(self, mock_git_merge_base):
        """Test MergeBaseValidator with valid merge base."""
        mock_git_merge_base.return_value = 0

        rule = ValidationRule(check="merge_base")
        validator = MergeBaseValidator(rule)
        context = ValidationContext()

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @patch("commit_check.util.git_merge_base")
    def test_merge_base_validator_invalid(self, mock_git_merge_base):
        """Test MergeBaseValidator with invalid merge base."""
        mock_git_merge_base.return_value = 1

        rule = ValidationRule(check="merge_base")
        validator = MergeBaseValidator(rule)
        context = ValidationContext()

        result = validator.validate(context)
        assert result == ValidationResult.FAIL


class TestValidationEngine:
    def test_validation_engine_creation(self):
        """Test ValidationEngine creation."""
        rules = [
            ValidationRule(check="message", pattern=r"^feat:"),
            ValidationRule(check="branch", pattern=r"^feature/"),
        ]
        engine = ValidationEngine(rules)
        assert len(engine.validators) == 2

    def test_validation_engine_validate_all_pass(self):
        """Test ValidationEngine with all validations passing."""
        rules = [ValidationRule(check="message", pattern=r"^feat:")]
        engine = ValidationEngine(rules)
        context = ValidationContext(stdin_text="feat: add feature")

        result = engine.validate_all(context)
        assert result == ValidationResult.PASS

    def test_validation_engine_validate_all_fail(self):
        """Test ValidationEngine with some validations failing."""
        rules = [
            ValidationRule(check="message", pattern=r"^feat:"),
            ValidationRule(check="message", pattern=r"^fix:"),  # This will fail
        ]
        engine = ValidationEngine(rules)
        context = ValidationContext(stdin_text="feat: add feature")

        result = engine.validate_all(context)
        assert result == ValidationResult.FAIL

    def test_validation_engine_empty_rules(self):
        """Test ValidationEngine with no rules."""
        engine = ValidationEngine([])
        context = ValidationContext()

        result = engine.validate_all(context)
        assert result == ValidationResult.PASS

    def test_validation_engine_unknown_validator_type(self):
        """Test ValidationEngine with unknown validator type."""
        rules = [ValidationRule(check="unknown_check")]

        with pytest.raises(ValueError, match="Unknown validator type: unknown_check"):
            ValidationEngine(rules)
