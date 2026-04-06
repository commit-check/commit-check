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
    @pytest.mark.benchmark
    def test_validation_result_enum(self):
        """Test ValidationResult enum values."""
        assert ValidationResult.PASS.value == 0
        assert ValidationResult.FAIL.value == 1


class TestValidationContext:
    @pytest.mark.benchmark
    def test_validation_context_creation(self):
        """Test ValidationContext creation and properties."""
        context = ValidationContext(
            stdin_text="test message", commit_file="/path/to/commit"
        )
        assert context.stdin_text == "test message"
        assert context.commit_file == "/path/to/commit"

    @pytest.mark.benchmark
    def test_validation_context_defaults(self):
        """Test ValidationContext with default values."""
        context = ValidationContext()
        assert context.stdin_text is None
        assert context.commit_file is None


class TestBaseValidator:
    @pytest.mark.benchmark
    def test_base_validator_is_abstract(self):
        """Test that BaseValidator cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseValidator()


class TestCommitMessageValidator:
    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
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
    @pytest.mark.benchmark
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
    @pytest.mark.benchmark
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
    @pytest.mark.benchmark
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
    @pytest.mark.benchmark
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
    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
    def test_validate_with_stdin_text(self):
        """Test branch validation with stdin_text."""
        rule = ValidationRule(check="branch", regex=r"^feature/")
        validator = BranchValidator(rule)
        context = ValidationContext(stdin_text="feature/new-feature")

        validator.validate(context)

    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_branch_name")
    @pytest.mark.benchmark
    def test_branch_validator_develop_branch_allowed(
        self, mock_get_branch_name, mock_has_commits
    ):
        """Test BranchValidator with develop branch when it's in allow_branch_names."""
        mock_has_commits.return_value = True
        mock_get_branch_name.return_value = "develop"
        # Regex pattern that includes develop as an allowed branch name
        rule = ValidationRule(
            check="branch",
            regex=r"^(feature|bugfix|hotfix)\/.+|(master)|(main)|(HEAD)|(PR-.+)|(develop)",
        )
        validator = BranchValidator(rule)
        config = {"branch": {"ignore_authors": []}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_branch_name")
    @pytest.mark.benchmark
    def test_branch_validator_staging_branch_allowed(
        self, mock_get_branch_name, mock_has_commits
    ):
        """Test BranchValidator with staging branch when it's in allow_branch_names."""
        mock_has_commits.return_value = True
        mock_get_branch_name.return_value = "staging"
        # Regex pattern that includes staging as an allowed branch name
        rule = ValidationRule(
            check="branch",
            regex=r"^(feature|bugfix|hotfix)\/.+|(master)|(main)|(HEAD)|(PR-.+)|(staging)|(develop)",
        )
        validator = BranchValidator(rule)
        config = {"branch": {"ignore_authors": []}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_branch_name")
    @pytest.mark.benchmark
    def test_branch_validator_develop_branch_not_allowed(
        self, mock_get_branch_name, mock_has_commits
    ):
        """Test BranchValidator with develop branch when it's NOT in allow_branch_names."""
        mock_has_commits.return_value = True
        mock_get_branch_name.return_value = "develop"
        # Regex pattern that does NOT include develop as an allowed branch name
        rule = ValidationRule(
            check="branch",
            regex=r"^(feature|bugfix|hotfix)\/.+|(master)|(main)|(HEAD)|(PR-.+)",
        )
        validator = BranchValidator(rule)
        config = {"branch": {"ignore_authors": []}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_validate_without_regex(self):
        """Test branch validation without regex (should pass)."""
        rule = ValidationRule(check="branch")
        validator = BranchValidator(rule)
        context = ValidationContext()

        result = validator.validate(context)
        assert result == ValidationResult.PASS


class TestAuthorValidator:
    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_git_config_value")
    @patch("commit_check.engine.get_commit_info")
    @pytest.mark.benchmark
    def test_author_validator_name_valid(
        self, mock_get_commit_info, mock_get_git_config_value, mock_has_commits
    ):
        """Test AuthorValidator for author name."""
        mock_has_commits.return_value = True
        mock_get_commit_info.return_value = "John Doe"
        mock_get_git_config_value.return_value = ""
        rule = ValidationRule(check="author_name", regex=r"^[A-Z][a-z]+ [A-Z][a-z]+$")
        validator = AuthorValidator(rule)
        config = {"commit": {"ignore_authors": ["ignored"]}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_git_config_value")
    @patch("commit_check.engine.get_commit_info")
    @pytest.mark.benchmark
    def test_author_validator_email_valid(
        self, mock_get_commit_info, mock_get_git_config_value, mock_has_commits
    ):
        """Test AuthorValidator for author email."""
        mock_has_commits.return_value = True
        mock_get_commit_info.return_value = "john.doe@example.com"
        mock_get_git_config_value.return_value = ""
        rule = ValidationRule(
            check="author_email",
            regex=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        )
        validator = AuthorValidator(rule)
        config = {"commit": {"ignore_authors": ["ignored"]}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.PASS
        # Called once for skip logic ("an"), once for co-author check ("b"), once for value ("ae")
        assert mock_get_commit_info.call_count == 3
        assert mock_get_commit_info.call_args_list[0][0][0] == "an"
        assert mock_get_commit_info.call_args_list[2][0][0] == "ae"
        assert result == ValidationResult.PASS
        # Called once for skip logic ("an"), once for co-author check ("b"), once for value ("ae")
        assert mock_get_commit_info.call_count == 3
        assert mock_get_commit_info.call_args_list[0][0][0] == "an"
        assert mock_get_commit_info.call_args_list[2][0][0] == "ae"

    @patch("commit_check.engine.get_commit_info")
    @pytest.mark.benchmark
    def test_author_validator_ignored_author(self, mock_get_commit_info):
        """Test AuthorValidator skips validation for ignored author."""
        mock_get_commit_info.return_value = "ignored"
        rule = ValidationRule(check="author_name", regex=r"^[A-Z][a-z]+ [A-Z][a-z]+$")
        validator = AuthorValidator(rule)
        config = {"commit": {"ignore_authors": ["ignored"]}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_validate_author_with_allowed_list(self):
        """Test author validation with allowed list."""
        rule = ValidationRule(check="author_name", allowed=["John Doe", "Jane Smith"])
        validator = AuthorValidator(rule)

        # Mock author value
        with patch.object(validator, "_get_author_value", return_value="John Doe"):
            context = ValidationContext()
            result = validator.validate(context)
            assert result == ValidationResult.PASS

    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
    def test_validate_author_in_ignored_list(self):
        """Test author validation with ignored authors."""
        rule = ValidationRule(check="author_name", ignored=["Bot User", "CI User"])
        validator = AuthorValidator(rule)

        # Mock author value
        with patch.object(validator, "_get_author_value", return_value="Bot User"):
            context = ValidationContext()
            result = validator.validate(context)
            assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_get_author_value_with_email_format(self):
        """Test _get_author_value with email format."""
        rule = ValidationRule(check="author_email")
        validator = AuthorValidator(rule)
        context = ValidationContext()

        with (
            patch("commit_check.engine.get_git_config_value", return_value=""),
            patch(
                "commit_check.engine.get_commit_info", return_value="test@example.com"
            ),
        ):
            author_value = validator._get_author_value(context)
            assert author_value == "test@example.com"


class TestCommitTypeValidator:
    @pytest.mark.benchmark
    def test_commit_type_validator_merge_commits(self):
        """Test CommitTypeValidator with merge commits."""
        rule = ValidationRule(check="allow_merge_commits", value=True)
        validator = CommitTypeValidator(rule)
        context = ValidationContext(stdin_text="Merge branch 'feature' into main")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_commit_type_validator_revert_commits(self):
        """Test CommitTypeValidator with revert commits."""
        rule = ValidationRule(check="allow_revert_commits", value=True)
        validator = CommitTypeValidator(rule)
        context = ValidationContext(stdin_text='Revert "feat: add feature"')

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
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
    @pytest.mark.benchmark
    def test_subject_length_validator_max_valid(self):
        """Test SubjectLengthValidator with valid max length."""
        rule = ValidationRule(check="subject_max_length", value=50)
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(stdin_text="feat: short message")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_subject_length_validator_max_too_long(self):
        """Test SubjectLengthValidator with message too long."""
        rule = ValidationRule(check="subject_max_length", value=20)
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(
            stdin_text="feat: this is a very long commit message that exceeds the limit"
        )

        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_subject_length_validator_min_valid(self):
        """Test SubjectLengthValidator with valid min length."""
        rule = ValidationRule(check="subject_min_length", value=10)
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_subject_length_validator_min_too_short(self):
        """Test SubjectLengthValidator with message too short."""
        rule = ValidationRule(check="subject_min_length", value=20)
        validator = SubjectLengthValidator(rule)
        context = ValidationContext(stdin_text="feat: fix")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL


class TestSignoffValidator:
    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
    def test_signoff_validator_missing_signoff(self):
        """Test SignoffValidator with missing signoff."""
        rule = ValidationRule(check="require_signed_off_by")
        validator = SignoffValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_validate_with_signoff_in_stdin(self):
        """Test signoff validation with stdin message containing signoff."""
        rule = ValidationRule(check="require_signed_off_by", regex=r".*Signed-off-by.*")
        validator = SignoffValidator(rule)
        context = ValidationContext(
            stdin_text="feat: add feature\n\nSigned-off-by: John Doe <john@example.com>"
        )

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_validate_without_signoff(self):
        """Test signoff validation without signoff."""
        rule = ValidationRule(check="require_signed_off_by")
        validator = SignoffValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature")

        with patch("commit_check.util._print_failure"):
            result = validator.validate(context)
            assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
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
    @pytest.mark.benchmark
    def test_subject_capitalization_validator_valid(self):
        """Test SubjectCapitalizationValidator with capitalized subject."""
        rule = ValidationRule(check="subject_capitalized")
        validator = SubjectCapitalizationValidator(rule)
        context = ValidationContext(stdin_text="feat: Add new feature")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_subject_capitalization_validator_not_capitalized(self):
        """Test SubjectCapitalizationValidator with non-capitalized subject."""
        rule = ValidationRule(check="subject_capitalized")
        validator = SubjectCapitalizationValidator(rule)
        context = ValidationContext(stdin_text="feat: add new feature")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL


class TestBodyValidator:
    @pytest.mark.benchmark
    def test_body_validator_with_body(self):
        """Test BodyValidator with commit body."""
        rule = ValidationRule(check="require_body")
        validator = BodyValidator(rule)
        context = ValidationContext(
            stdin_text="feat: add feature\n\nThis is the commit body"
        )

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_body_validator_no_body(self):
        """Test BodyValidator without commit body."""
        rule = ValidationRule(check="require_body")
        validator = BodyValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature")

        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_validate_with_body_present(self):
        """Test body validation with body present."""
        rule = ValidationRule(check="require_body")
        validator = BodyValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature\n\nThis is the body")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_validate_with_empty_lines_and_body(self):
        """Test body validation with empty lines before body."""
        rule = ValidationRule(check="require_body")
        validator = BodyValidator(rule)
        context = ValidationContext(
            stdin_text="feat: add feature\n\n\nThis is the body"
        )

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
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
    @pytest.mark.benchmark
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
    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
    def test_validate_with_merge_base_ahead(self):
        """Test merge base validation when branch is ahead."""
        rule = ValidationRule(check="merge_base")
        validator = MergeBaseValidator(rule)
        context = ValidationContext()

        with patch("commit_check.engine.git_merge_base", return_value=0):
            result = validator.validate(context)
            assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_validate_with_merge_base_skip_conditions(self):
        """Test merge base validation skip conditions."""
        rule = ValidationRule(check="merge_base")
        validator = MergeBaseValidator(rule)
        context = ValidationContext()  # No stdin, should skip if no commits

        with patch("commit_check.engine.has_commits", return_value=False):
            result = validator.validate(context)
            assert result == ValidationResult.PASS  # Skipped


class TestValidationEngine:
    @pytest.mark.benchmark
    def test_validation_engine_creation(self):
        """Test ValidationEngine creation."""
        rules = [
            ValidationRule(check="message", regex=r"^feat:"),
            ValidationRule(check="branch", regex=r"^feature/"),
        ]
        engine = ValidationEngine(rules)

        assert len(engine.rules) == 2
        assert engine.rules == rules

    @pytest.mark.benchmark
    def test_validation_engine_validate_all_pass(self):
        """Test ValidationEngine with all validations passing."""
        rules = [ValidationRule(check="message", regex=r"^feat:")]
        engine = ValidationEngine(rules)
        context = ValidationContext(stdin_text="feat: add feature")

        result = engine.validate_all(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
    def test_validation_engine_empty_rules(self):
        """Test ValidationEngine with no rules."""
        engine = ValidationEngine([])
        context = ValidationContext()

        result = engine.validate_all(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_validation_engine_unknown_validator_type(self):
        """Test ValidationEngine with unknown validator type."""
        rules = [ValidationRule(check="unknown_check", regex=r".*")]
        engine = ValidationEngine(rules)
        context = ValidationContext()

        # Should not raise an error, just skip unknown validators
        result = engine.validate_all(context)
        assert result == ValidationResult.PASS  # No validation performed = PASS

    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
    def test_validation_engine_validator_map(self):
        """Test ValidationEngine VALIDATOR_MAP contains expected mappings."""
        engine = ValidationEngine([])

        expected_mappings = {
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

        for check, validator_class in expected_mappings.items():
            assert engine.VALIDATOR_MAP[check] == validator_class


class TestSubjectValidator:
    """Test SubjectValidator base class."""

    @pytest.mark.benchmark
    def test_get_subject_with_context_stdin(self):
        """Test _get_subject with stdin_text."""
        rule = ValidationRule(check="subject_capitalized")
        validator = SubjectCapitalizationValidator(rule)
        context = ValidationContext(stdin_text="feat: add new feature")

        subject = validator._get_subject(context)
        assert subject == "feat: add new feature"

    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
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

    @pytest.mark.benchmark
    def test_validate_with_imperative_subject(self):
        """Test validation with proper imperative subject."""
        rule = ValidationRule(check="subject_imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text="fix: resolve the issue")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_validate_with_non_imperative_subject(self):
        """Test validation with non-imperative subject."""
        rule = ValidationRule(check="subject_imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text="fix: resolved the issue")

        # Mock the print function to avoid output during tests
        with patch("commit_check.util._print_failure"):
            result = validator.validate(context)
            assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_validate_short_subject(self):
        """Test validation with very short subject (edge case)."""
        rule = ValidationRule(check="subject_imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text="feat: add")

        # "add" is a valid imperative word with conventional prefix
        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_validate_with_breaking_change(self):
        """Test validation with breaking change notation."""
        rule = ValidationRule(check="subject_imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text="feat!: update authentication system")

        # "update" is a valid imperative word with breaking change notation
        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_validate_with_scoped_breaking_change(self):
        """Test validation with scoped breaking change notation."""
        rule = ValidationRule(check="subject_imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text="fix(auth)!: resolve login bug")

        # "resolve" is a valid imperative word with scope and breaking change notation
        result = validator.validate(context)
        assert result == ValidationResult.PASS


class TestCoAuthorSkip:
    """Tests for co-author bypass logic in _should_skip_commit_validation."""

    @pytest.mark.benchmark
    def test_co_author_in_ignore_list_skips_validation(self):
        """Test that a commit with a co-author in ignore_authors is skipped."""
        rule = ValidationRule(
            check="message",
            regex=r"^(feat|fix): .+",
            error="Bad commit",
            suggest="Use conventional format",
        )
        validator = CommitMessageValidator(rule)

        message = "Update README\n\nCo-authored-by: coderabbitai[bot] <bot@example.com>"
        config = {"commit": {"ignore_authors": ["coderabbitai[bot]"]}}
        context = ValidationContext(stdin_text=message, config=config)

        with patch("commit_check.engine.get_commit_info", return_value="other-author"):
            result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_co_author_not_in_ignore_list_does_not_skip(self):
        """Test that co-author not in ignore list does not bypass validation."""
        rule = ValidationRule(
            check="message",
            regex=r"^(feat|fix): .+",
            error="Bad commit",
            suggest="Use conventional format",
        )
        validator = CommitMessageValidator(rule)

        message = "Update README\n\nCo-authored-by: someuser <user@example.com>"
        config = {"commit": {"ignore_authors": ["coderabbitai[bot]"]}}
        context = ValidationContext(stdin_text=message, config=config)

        with patch("commit_check.engine.get_commit_info", return_value="other-author"):
            with patch("commit_check.util._print_failure"):
                result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_co_author_in_ignore_list_from_commit_file(self):
        """Test co-author skip logic when message comes from a commit file."""
        import tempfile
        import os

        rule = ValidationRule(
            check="message",
            regex=r"^(feat|fix): .+",
            error="Bad commit",
            suggest="Use conventional format",
        )
        validator = CommitMessageValidator(rule)

        message = "Update docs\n\nCo-authored-by: dependabot[bot] <bot@github.com>"
        config = {"commit": {"ignore_authors": ["dependabot[bot]"]}}

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(message)
            commit_file = f.name

        try:
            context = ValidationContext(commit_file=commit_file, config=config)
            with patch(
                "commit_check.engine.get_commit_info", return_value="main-author"
            ):
                result = validator.validate(context)
            assert result == ValidationResult.PASS
        finally:
            os.unlink(commit_file)


class TestGetGitConfigValue:
    """Tests for the AuthorValidator using git config (Issue #298)."""

    @pytest.mark.benchmark
    def test_author_name_uses_git_config_when_available(self):
        """Author name validation uses git config user.name when set."""
        rule = ValidationRule(
            check="author_name",
            regex=r"^[A-Za-z ]+$",
            error="Invalid author name",
            suggest="Set a valid name",
        )
        validator = AuthorValidator(rule)
        context = ValidationContext()

        with (
            patch("commit_check.engine.get_commit_info", return_value="some-author"),
            patch(
                "commit_check.engine.get_git_config_value",
                return_value="01 Invalid Name",
            ),
        ):
            with patch("commit_check.util._print_failure"):
                result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_author_name_falls_back_to_git_log_when_config_empty(self):
        """Author name validation falls back to git log when git config is empty."""
        rule = ValidationRule(
            check="author_name",
            regex=r"^[A-Za-z ]+$",
            error="Invalid author name",
            suggest="Set a valid name",
        )
        validator = AuthorValidator(rule)
        context = ValidationContext()

        with (
            patch("commit_check.engine.get_git_config_value", return_value=""),
            patch("commit_check.engine.get_commit_info", return_value="Valid Name"),
        ):
            result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_author_email_uses_git_config_when_available(self):
        """Author email validation uses git config user.email when set."""
        rule = ValidationRule(
            check="author_email",
            regex=r"^.+@.+$",
            error="Invalid email",
            suggest="Set a valid email",
        )
        validator = AuthorValidator(rule)
        context = ValidationContext()

        with (
            patch("commit_check.engine.get_commit_info", return_value="some-author"),
            patch(
                "commit_check.engine.get_git_config_value",
                return_value="user@example.com",
            ),
        ):
            result = validator.validate(context)
        assert result == ValidationResult.PASS


class TestIgnoreAuthorsGitConfig:
    """Tests that ignore_authors also matches the git config identity.

    When a bot (e.g. pre-commit-ci[bot]) runs hooks at the commit-msg stage,
    the commit has not been created yet, so get_commit_info("an") returns the
    PREVIOUS commit's author.  The fix is to also check git config user.name
    and user.email against ignore_authors.
    """

    @pytest.mark.benchmark
    def test_commit_skip_via_git_config_user_name(self):
        """Commit validation is skipped when git config user.name is in ignore_authors."""
        rule = ValidationRule(
            check="message",
            regex=r"^(feat|fix): .+",
            error="Bad commit",
            suggest="Use conventional format",
        )
        validator = CommitMessageValidator(rule)
        config = {"commit": {"ignore_authors": ["pre-commit-ci[bot]"]}}
        # stdin_text has an invalid message that would otherwise fail
        context = ValidationContext(
            stdin_text="not a conventional commit", config=config
        )

        def git_config_side_effect(key):
            return "pre-commit-ci[bot]" if key == "user.name" else ""

        with (
            patch(
                "commit_check.engine.get_git_config_value",
                side_effect=git_config_side_effect,
            ),
            patch("commit_check.engine.get_commit_info", return_value="other-author"),
        ):
            result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_commit_skip_via_git_config_user_email(self):
        """Commit validation is skipped when git config user.email is in ignore_authors."""
        rule = ValidationRule(
            check="message",
            regex=r"^(feat|fix): .+",
            error="Bad commit",
            suggest="Use conventional format",
        )
        validator = CommitMessageValidator(rule)
        config = {"commit": {"ignore_authors": ["bot@example.com"]}}
        context = ValidationContext(
            stdin_text="not a conventional commit", config=config
        )

        def git_config_side_effect(key):
            return "bot@example.com" if key == "user.email" else "Some Bot"

        with (
            patch(
                "commit_check.engine.get_git_config_value",
                side_effect=git_config_side_effect,
            ),
            patch("commit_check.engine.get_commit_info", return_value="other-author"),
        ):
            result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_branch_skip_via_git_config_user_name(self):
        """Branch validation is skipped when git config user.name is in ignore_authors."""
        rule = ValidationRule(
            check="branch",
            regex=r"^(feature|bugfix)/.+",
            error="Bad branch",
            suggest="Use conventional branch",
        )
        validator = BranchValidator(rule)
        config = {"branch": {"ignore_authors": ["pre-commit-ci[bot]"]}}
        context = ValidationContext(config=config)

        def git_config_side_effect(key):
            return "pre-commit-ci[bot]" if key == "user.name" else ""

        with (
            patch(
                "commit_check.engine.get_git_config_value",
                side_effect=git_config_side_effect,
            ),
            patch("commit_check.engine.get_commit_info", return_value="other-author"),
            patch(
                "commit_check.engine.get_branch_name",
                return_value="pre-commit-ci-update-config",
            ),
            patch("commit_check.engine.has_commits", return_value=True),
        ):
            result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_branch_skip_via_git_config_user_email(self):
        """Branch validation is skipped when git config user.email is in ignore_authors."""
        rule = ValidationRule(
            check="branch",
            regex=r"^(feature|bugfix)/.+",
            error="Bad branch",
            suggest="Use conventional branch",
        )
        validator = BranchValidator(rule)
        config = {"branch": {"ignore_authors": ["bot@example.com"]}}
        context = ValidationContext(config=config)

        def git_config_side_effect(key):
            return "bot@example.com" if key == "user.email" else "Some Bot"

        with (
            patch(
                "commit_check.engine.get_git_config_value",
                side_effect=git_config_side_effect,
            ),
            patch("commit_check.engine.get_commit_info", return_value="other-author"),
            patch(
                "commit_check.engine.get_branch_name",
                return_value="pre-commit-ci-update-config",
            ),
            patch("commit_check.engine.has_commits", return_value=True),
        ):
            result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_commit_not_skipped_when_git_config_not_in_ignore_list(self):
        """Commit validation is NOT skipped when git config user is not in ignore_authors."""
        rule = ValidationRule(
            check="message",
            regex=r"^(feat|fix): .+",
            error="Bad commit",
            suggest="Use conventional format",
        )
        validator = CommitMessageValidator(rule)
        config = {"commit": {"ignore_authors": ["pre-commit-ci[bot]"]}}
        context = ValidationContext(
            stdin_text="not a conventional commit", config=config
        )

        def git_config_side_effect(key):
            return "regular-developer" if key == "user.name" else "dev@example.com"

        with (
            patch(
                "commit_check.engine.get_git_config_value",
                side_effect=git_config_side_effect,
            ),
            patch("commit_check.engine.get_commit_info", return_value="other-author"),
            patch("commit_check.util._print_failure"),
        ):
            result = validator.validate(context)
        assert result == ValidationResult.FAIL
