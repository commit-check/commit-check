"""Tests for commit_check.engine module."""

import pytest
import tempfile
import os
from unittest.mock import mock_open, patch
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
            regex=r"^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .+",
        )
        validator = CommitMessageValidator(rule)
        context = ValidationContext(stdin_text="feat: add new feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_commit_message_validator_invalid_commit(self):
        """Test CommitMessageValidator with invalid commit message."""
        rule = ValidationRule(
            check="message",
            regex=r"^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .+",
        )
        validator = CommitMessageValidator(rule)
        context = ValidationContext(stdin_text="invalid commit message")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    def test_commit_message_validator_with_file(self):
        """Test CommitMessageValidator reading from file."""
        rule = ValidationRule(check="message", regex=r"^(feat|fix):")
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

    @patch("commit_check.engine.get_commit_info")
    def test_commit_message_validator_file_not_found(self, mock_get_commit_info):
        """Test CommitMessageValidator with non-existent file."""
        # Mock git fallback to return a message that doesn't match regex
        mock_get_commit_info.side_effect = lambda format_str: {
            "s": "invalid commit message",
            "b": "",
            "an": "author",
        }[format_str]

        rule = ValidationRule(check="message", regex=r"^feat:")
        validator = CommitMessageValidator(rule)
        context = ValidationContext(commit_file="/nonexistent/file")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @patch("commit_check.engine.get_commit_info")
    def test_commit_message_validator_from_git(self, mock_get_commit_info):
        """Test CommitMessageValidator reading from git."""
        # Mock both subject ("s") and body ("b") calls
        mock_get_commit_info.side_effect = lambda format_str: {
            "s": "feat: add feature from git",
            "b": "",
        }.get(format_str, "")

        rule = ValidationRule(check="message", regex=r"^feat:")
        validator = CommitMessageValidator(rule)
        context = ValidationContext()

        result = validator.validate(context)
        assert result == ValidationResult.PASS
        # Should call get_commit_info three times: subject, body, and author
        assert mock_get_commit_info.call_count == 3


class TestBranchValidator:
    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_branch_name")
    def test_branch_validator_valid_branch(
        self, mock_get_branch_name, mock_has_commits
    ):
        """Test BranchValidator with valid branch name."""
        mock_has_commits.return_value = True
        mock_get_branch_name.return_value = "feature/new-feature"
        rule = ValidationRule(check="branch", regex=r"^(feature|bugfix|hotfix)/.+")
        validator = BranchValidator(rule)
        config = {"branch": {"ignore_authors": ["ignored"]}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.PASS
        assert result == ValidationResult.PASS
        assert result == ValidationResult.PASS

    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_branch_name")
    def test_branch_validator_invalid_branch(
        self, mock_get_branch_name, mock_has_commits
    ):
        """Test BranchValidator with invalid branch name."""
        mock_has_commits.return_value = True
        mock_get_branch_name.return_value = "invalid-branch-name"
        rule = ValidationRule(check="branch", regex=r"^(feature|bugfix|hotfix)/.+")
        validator = BranchValidator(rule)
        config = {"branch": {"ignore_authors": ["ignored"]}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @patch("commit_check.engine.get_branch_name")
    @patch("commit_check.engine.get_commit_info")
    def test_branch_validator_ignored_author(
        self, mock_get_commit_info, mock_get_branch_name
    ):
        """Test BranchValidator skips validation for ignored author."""
        mock_get_branch_name.return_value = "invalid-branch-name"
        mock_get_commit_info.return_value = "ignored"
        rule = ValidationRule(check="branch", regex=r"^(feature|bugfix|hotfix)/.+")
        validator = BranchValidator(rule)
        config = {"branch": {"ignore_authors": ["ignored"]}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_validate_with_stdin_text(self):
        """Test branch validation with stdin_text."""
        rule = ValidationRule(check="branch", regex=r"^feature/")
        validator = BranchValidator(rule)
        context = ValidationContext(stdin_text="feature/new-feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_validate_without_regex(self):
        """Test branch validation without regex (should pass)."""
        rule = ValidationRule(check="branch")
        validator = BranchValidator(rule)
        context = ValidationContext()

        result = validator.validate(context)
        assert result == ValidationResult.PASS


class TestAuthorValidator:
    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_commit_info")
    def test_author_validator_name_valid(self, mock_get_commit_info, mock_has_commits):
        """Test AuthorValidator for author name."""
        mock_has_commits.return_value = True
        mock_get_commit_info.return_value = "John Doe"
        rule = ValidationRule(check="author_name", regex=r"^[A-Z][a-z]+ [A-Z][a-z]+$")
        validator = AuthorValidator(rule)
        config = {"commit": {"ignore_authors": ["ignored"]}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_commit_info")
    def test_author_validator_email_valid(self, mock_get_commit_info, mock_has_commits):
        """Test AuthorValidator for author email."""
        mock_has_commits.return_value = True
        mock_get_commit_info.return_value = "john.doe@example.com"
        rule = ValidationRule(
            check="author_email",
            regex=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        )
        validator = AuthorValidator(rule)
        config = {"commit": {"ignore_authors": ["ignored"]}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.PASS
        # Called once for skip logic ("an"), once for value ("ae")
        assert mock_get_commit_info.call_count == 2
        assert mock_get_commit_info.call_args_list[0][0][0] == "an"
        assert mock_get_commit_info.call_args_list[1][0][0] == "ae"
        assert result == ValidationResult.PASS
        # Called once for skip logic ("an"), once for value ("ae")
        assert mock_get_commit_info.call_count == 2
        assert mock_get_commit_info.call_args_list[0][0][0] == "an"
        assert mock_get_commit_info.call_args_list[1][0][0] == "ae"

    @patch("commit_check.engine.get_commit_info")
    def test_author_validator_ignored_author(self, mock_get_commit_info):
        """Test AuthorValidator skips validation for ignored author."""
        mock_get_commit_info.return_value = "ignored"
        rule = ValidationRule(check="author_name", regex=r"^[A-Z][a-z]+ [A-Z][a-z]+$")
        validator = AuthorValidator(rule)
        config = {"commit": {"ignore_authors": ["ignored"]}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_validate_author_with_allowed_list(self):
        """Test author validation with allowed list."""
        rule = ValidationRule(check="author_name", allowed=["John Doe", "Jane Smith"])
        validator = AuthorValidator(rule)

        # Mock author value
        with patch.object(validator, "_get_author_value", return_value="John Doe"):
            context = ValidationContext()
            result = validator.validate(context)
            assert result == ValidationResult.PASS

    def test_validate_author_not_in_allowed_list(self):
        """Test author validation with name not in allowed list."""
        rule = ValidationRule(check="author_name", allowed=["John Doe", "Jane Smith"])
        validator = AuthorValidator(rule)

        # Mock author value and print function
        with patch.object(validator, "_get_author_value", return_value="Unknown User"):
            with patch("commit_check.util._print_failure"):
                context = ValidationContext()
                result = validator.validate(context)
                assert result == ValidationResult.FAIL

    def test_validate_author_in_ignored_list(self):
        """Test author validation with ignored authors."""
        rule = ValidationRule(check="author_name", ignored=["Bot User", "CI User"])
        validator = AuthorValidator(rule)

        # Mock author value
        with patch.object(validator, "_get_author_value", return_value="Bot User"):
            context = ValidationContext()
            result = validator.validate(context)
            assert result == ValidationResult.PASS

    def test_get_author_value_with_email_format(self):
        """Test _get_author_value with email format."""
        rule = ValidationRule(check="author_email")
        validator = AuthorValidator(rule)
        context = ValidationContext()

        with patch(
            "commit_check.engine.get_commit_info", return_value="test@example.com"
        ):
            author_value = validator._get_author_value(context)
            assert author_value == "test@example.com"


class TestCommitTypeValidator:
    def test_commit_type_validator_merge_commits(self):
        """Test CommitTypeValidator with merge commits."""
        rule = ValidationRule(check="allow_merge_commits", value=True)
        validator = CommitTypeValidator(rule)
        context = ValidationContext(stdin_text="Merge branch 'feature' into main")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_commit_type_validator_revert_commits(self):
        """Test CommitTypeValidator with revert commits."""
        rule = ValidationRule(check="allow_revert_commits", value=True)
        validator = CommitTypeValidator(rule)
        context = ValidationContext(stdin_text='Revert "feat: add feature"')

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_validate_merge_commit_allowed(self):
        """Test merge commit validation when allowed."""
        rule = ValidationRule(check="allow_merge_commits", value=True)
        validator = CommitTypeValidator(rule)
        context = ValidationContext()

        with patch("commit_check.engine.get_commit_info") as mock_get_info:
            mock_get_info.side_effect = lambda x: {
                "s": "Merge branch 'feature'",
                "b": "",
                "an": "test-author",
            }[x]

            result = validator.validate(context)
            assert result == ValidationResult.PASS

    def test_validate_merge_commit_not_allowed(self):
        """Test merge commit validation when not allowed."""
        rule = ValidationRule(check="allow_merge_commits", value=False)
        validator = CommitTypeValidator(rule)
        context = ValidationContext()

        with patch("commit_check.engine.get_commit_info") as mock_get_info:
            mock_get_info.side_effect = lambda x: {
                "s": "Merge branch 'feature'",
                "b": "",
                "an": "test-author",
            }[x]

            with patch("commit_check.util._print_failure"):
                result = validator.validate(context)
                assert result == ValidationResult.FAIL

    def test_validate_revert_commit_allowed(self):
        """Test revert commit validation when allowed."""
        rule = ValidationRule(check="allow_revert_commits", value=True)
        validator = CommitTypeValidator(rule)
        context = ValidationContext()

        with patch("commit_check.engine.get_commit_info") as mock_get_info:
            mock_get_info.side_effect = lambda x: {
                "s": "Revert 'bad commit'",
                "b": "",
                "an": "test-author",
            }[x]

            result = validator.validate(context)
            assert result == ValidationResult.PASS

    def test_validate_fixup_commit_not_allowed(self):
        """Test fixup commit validation when not allowed."""
        rule = ValidationRule(check="allow_fixup_commits", value=False)
        validator = CommitTypeValidator(rule)
        context = ValidationContext()

        with patch("commit_check.engine.get_commit_info") as mock_get_info:
            mock_get_info.side_effect = lambda x: {
                "s": "fixup! fix bug",
                "b": "",
                "an": "test-author",
            }[x]

            with patch("commit_check.util._print_failure"):
                result = validator.validate(context)
                assert result == ValidationResult.FAIL

    def test_validate_wip_commit_allowed(self):
        """Test WIP commit validation when allowed."""
        rule = ValidationRule(check="allow_wip_commits", value=True)
        validator = CommitTypeValidator(rule)
        context = ValidationContext()

        with patch("commit_check.engine.get_commit_info") as mock_get_info:
            mock_get_info.side_effect = lambda x: {
                "s": "WIP: work in progress",
                "b": "",
                "an": "test-author",
            }[x]

            result = validator.validate(context)
            assert result == ValidationResult.PASS


class TestSubjectLengthValidator:
    def test_subject_length_validator_max_valid(self):
        """Test SubjectLengthValidator with valid max length."""
        rule = ValidationRule(check="subject_max_length", value=50)
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(stdin_text="feat: short message")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_subject_length_validator_max_too_long(self):
        """Test SubjectLengthValidator with message too long."""
        rule = ValidationRule(check="subject_max_length", value=20)
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(
            stdin_text="feat: this is a very long commit message that exceeds the limit"
        )

        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    def test_subject_length_validator_min_valid(self):
        """Test SubjectLengthValidator with valid min length."""
        rule = ValidationRule(check="subject_min_length", value=10)
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_subject_length_validator_min_too_short(self):
        """Test SubjectLengthValidator with message too short."""
        rule = ValidationRule(check="subject_min_length", value=20)
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(stdin_text="feat: fix")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL


class TestSignoffValidator:
    def test_signoff_validator_valid(self):
        """Test SignoffValidator with valid signoff."""
        rule = ValidationRule(
            check="require_signed_off_by", regex=r"Signed-off-by: .+ <.+@.+\..+>"
        )
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

    def test_validate_with_signoff_in_stdin(self):
        """Test signoff validation with stdin message containing signoff."""
        rule = ValidationRule(check="require_signed_off_by", regex=r".*Signed-off-by.*")
        validator = SignoffValidator(rule)
        context = ValidationContext(
            stdin_text="feat: add feature\n\nSigned-off-by: John Doe <john@example.com>"
        )

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_validate_without_signoff(self):
        """Test signoff validation without signoff."""
        rule = ValidationRule(check="require_signed_off_by")
        validator = SignoffValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature")

        with patch("commit_check.util._print_failure"):
            result = validator.validate(context)
            assert result == ValidationResult.FAIL

    def test_get_commit_message_from_context_file(self):
        """Test _get_commit_message with commit_file."""
        rule = ValidationRule(check="require_signed_off_by")
        validator = SignoffValidator(rule)
        context = ValidationContext(commit_file="dummy")

        with patch("commit_check.engine.get_commit_info") as mock_get_info:
            mock_get_info.side_effect = lambda x: {"s": "test message", "b": ""}[x]
            message = validator._get_commit_message(context)
            assert message == "test message"


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

    def test_validate_with_body_present(self):
        """Test body validation with body present."""
        rule = ValidationRule(check="require_body")
        validator = BodyValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature\n\nThis is the body")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_validate_with_empty_lines_and_body(self):
        """Test body validation with empty lines before body."""
        rule = ValidationRule(check="require_body")
        validator = BodyValidator(rule)
        context = ValidationContext(
            stdin_text="feat: add feature\n\n\nThis is the body"
        )

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_validate_without_body(self):
        """Test body validation without body."""
        rule = ValidationRule(check="require_body")
        validator = BodyValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature")

        with patch("commit_check.util._print_failure"):
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

    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_branch_name")
    @patch("commit_check.util.git_merge_base")
    def test_merge_base_validator_invalid(
        self, mock_git_merge_base, mock_get_branch_name, mock_has_commits
    ):
        """Test MergeBaseValidator with invalid merge base."""
        mock_has_commits.return_value = True
        mock_get_branch_name.return_value = "feature/test"
        mock_git_merge_base.return_value = 1

        rule = ValidationRule(check="merge_base", regex=r"^main$")
        validator = MergeBaseValidator(rule)
        context = ValidationContext()

        # Mock _find_target_branch to return a target branch
        with patch.object(validator, "_find_target_branch", return_value="main"):
            result = validator.validate(context)
        assert result == ValidationResult.FAIL

    def test_validate_with_merge_base_ahead(self):
        """Test merge base validation when branch is ahead."""
        rule = ValidationRule(check="merge_base")
        validator = MergeBaseValidator(rule)
        context = ValidationContext()

        with patch("commit_check.engine.git_merge_base", return_value=0):
            result = validator.validate(context)
            assert result == ValidationResult.PASS

    def test_validate_with_merge_base_skip_conditions(self):
        """Test merge base validation skip conditions."""
        rule = ValidationRule(check="merge_base")
        validator = MergeBaseValidator(rule)
        context = ValidationContext()  # No stdin, should skip if no commits

        with patch("commit_check.engine.has_commits", return_value=False):
            result = validator.validate(context)
            assert result == ValidationResult.PASS  # Skipped


class TestValidationEngine:
    def test_validation_engine_creation(self):
        """Test ValidationEngine creation."""
        rules = [
            ValidationRule(check="message", regex=r"^feat:"),
            ValidationRule(check="branch", regex=r"^feature/"),
        ]
        engine = ValidationEngine(rules)

        assert len(engine.rules) == 2
        assert engine.rules == rules

    def test_validation_engine_validate_all_pass(self):
        """Test ValidationEngine with all validations passing."""
        rules = [ValidationRule(check="message", regex=r"^feat:")]
        engine = ValidationEngine(rules)
        context = ValidationContext(stdin_text="feat: add feature")

        result = engine.validate_all(context)
        assert result == ValidationResult.PASS

    def test_validation_engine_validate_all_fail(self):
        """Test ValidationEngine with some validations failing."""
        rules = [
            ValidationRule(check="message", regex=r"^feat:"),
            ValidationRule(check="message", regex=r"^fix:"),  # This will fail
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
        rules = [ValidationRule(check="unknown_check", regex=r".*")]
        engine = ValidationEngine(rules)
        context = ValidationContext()

        # Should not raise an error, just skip unknown validators
        result = engine.validate_all(context)
        assert result == ValidationResult.PASS  # No validation performed = PASS

    def test_validate_all_with_unknown_validator(self):
        """Test validation engine with unknown validator type."""
        rules = [
            ValidationRule(check="unknown_check_type", regex=r".*"),
            ValidationRule(check="message", regex=r"^feat:"),
        ]
        engine = ValidationEngine(rules)
        context = ValidationContext(stdin_text="feat: add feature")

        result = engine.validate_all(context)
        assert (
            result == ValidationResult.PASS
        )  # Unknown validator skipped, remaining passes

    def test_validate_all_mixed_results(self):
        """Test validation engine with mixed pass/fail results."""
        rules = [
            ValidationRule(check="message", regex=r"^feat:"),  # Will pass
            ValidationRule(check="subject_max_length", value=5),  # Will fail
        ]
        engine = ValidationEngine(rules)
        context = ValidationContext(stdin_text="feat: add new feature")

        with patch("commit_check.util._print_failure"):
            result = engine.validate_all(context)
            assert result == ValidationResult.FAIL  # Any failure = overall failure


class TestSubjectValidator:
    """Test SubjectValidator base class."""

    def test_get_subject_with_context_stdin(self):
        """Test _get_subject with stdin_text."""
        rule = ValidationRule(check="subject_capitalized")
        validator = SubjectCapitalizationValidator(rule)
        context = ValidationContext(stdin_text="feat: add new feature")

        subject = validator._get_subject(context)
        assert subject == "feat: add new feature"

    def test_get_subject_with_context_file(self):
        """Test _get_subject with commit_file."""
        rule = ValidationRule(check="subject_capitalized")
        validator = SubjectCapitalizationValidator(rule)
        context = ValidationContext(commit_file="dummy")

        with patch(
            "builtins.open", mock_open(read_data="fix: resolve bug\n\nBody text")
        ):
            subject = validator._get_subject(context)
            assert subject == "fix: resolve bug"

    def test_get_subject_fallback_to_git(self):
        """Test _get_subject fallback to git."""
        rule = ValidationRule(check="subject_capitalized")
        validator = SubjectCapitalizationValidator(rule)
        context = ValidationContext()

        with patch(
            "commit_check.engine.get_commit_info", return_value="chore: update deps"
        ):
            subject = validator._get_subject(context)
            assert subject == "chore: update deps"

    def test_get_subject_with_file_not_found(self):
        """Test _get_subject when commit file not found."""
        rule = ValidationRule(check="subject_capitalized")
        validator = SubjectCapitalizationValidator(rule)
        context = ValidationContext(commit_file="/nonexistent/file")

        with patch(
            "commit_check.engine.get_commit_info", return_value="fallback message"
        ):
            subject = validator._get_subject(context)
            assert subject == "fallback message"


class TestSubjectImperativeValidator:
    """Test SubjectImperativeValidator edge cases."""

    def test_validate_with_imperative_subject(self):
        """Test validation with proper imperative subject."""
        rule = ValidationRule(check="imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text="fix: resolve the issue")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_validate_with_non_imperative_subject(self):
        """Test validation with non-imperative subject."""
        rule = ValidationRule(check="imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text="fix: resolved the issue")

        # Mock the print function to avoid output during tests
        with patch("commit_check.util._print_failure"):
            result = validator.validate(context)
            assert result == ValidationResult.FAIL

    def test_validate_short_subject(self):
        """Test validation with very short subject (edge case)."""
        rule = ValidationRule(check="imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text="feat: add")

        # "add" is a valid imperative word with conventional prefix
        result = validator.validate(context)
        assert result == ValidationResult.PASS
