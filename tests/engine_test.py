"""Tests for commit_check.engine module."""

import subprocess
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
    ForcePushValidator,
    AiAttributionValidator,
)
from commit_check.rule_builder import ValidationRule, RuleBuilder

# String constants used across tests (defined once to avoid duplication)
GIT_CONFIG_VALUE = "commit_check.engine.get_git_config_value"
FETCH_REMOTE_REF = "commit_check.engine.fetch_remote_ref"
GET_GIT_REMOTES = "commit_check.engine.get_git_remotes"
REFS_HEADS_MAIN = "refs/heads/main"
CONVENTIONAL_COMMIT_REGEX = r"^(feat|fix): .+"
BAD_COMMIT_MSG = "Bad commit"
USE_CONVENTIONAL_FORMAT = "Use conventional format"


def _pull_request_shaped_clone(tmp_path):
    """Build a clone shaped like a CI checkout of a pull request.

    One commit on origin/main, one commit of work on top, then every local
    branch removed and HEAD detached — so the target exists only as a
    remote-tracking ref and the branch name resolves to nothing.

    Returns the clone path.
    """
    import subprocess as sp

    def git(*args, cwd):
        return sp.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            text=True,
        )

    origin = tmp_path / "origin"
    origin.mkdir()
    git("init", "-q", "-b", "main", ".", cwd=origin)
    git("config", "user.name", "Dev", cwd=origin)
    git("config", "user.email", "dev@example.com", cwd=origin)
    git("commit", "-q", "--allow-empty", "-m", "feat: base", cwd=origin)

    clone = tmp_path / "clone"
    git("clone", "-q", str(origin), str(clone), cwd=tmp_path)
    git("config", "user.name", "Dev", cwd=clone)
    git("config", "user.email", "dev@example.com", cwd=clone)
    git("checkout", "-q", "-b", "feat/work", cwd=clone)
    git("commit", "-q", "--allow-empty", "-m", "feat: work", cwd=clone)
    return clone, git


def _diverged_merge_ref_clone(tmp_path):
    """Extend the pull-request shape into the one that hides false passes.

    Publishes feat/work, moves main past it so the branch is genuinely behind,
    then detaches at a merge of the two — the shape of GitHub's synthetic merge
    commit, whose first parent is the target tip. Every local branch is removed,
    so the branch resolves only through refs/remotes/origin/feat/work.
    """
    clone, git = _pull_request_shaped_clone(tmp_path)
    git("push", "-q", "origin", "feat/work", cwd=clone)
    origin = tmp_path / "origin"
    git("commit", "-q", "--allow-empty", "-m", "feat: main moved on", cwd=origin)
    git("fetch", "-q", "origin", cwd=clone)
    git("checkout", "-q", "--detach", "origin/main", cwd=clone)
    git(
        "merge",
        "-q",
        "--no-ff",
        "-m",
        "Merge feat/work into main",
        "feat/work",
        cwd=clone,
    )
    git("branch", "-q", "-D", "main", "feat/work", cwd=clone)
    return clone, git


def _validate_merge_base(clone, branch="feat/work", target="main"):
    """Run MergeBaseValidator inside ``clone`` as a CI checkout would."""
    cwd = os.getcwd()
    try:
        os.chdir(clone)
        with patch.dict(os.environ, {"GITHUB_HEAD_REF": branch}):
            validator = MergeBaseValidator(
                ValidationRule(check="merge_base", regex=target)
            )
            return validator.validate(ValidationContext(no_banner=True))
    finally:
        os.chdir(cwd)


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
        # Should call get_commit_info twice: subject and body
        # (author lookup is skipped when ignore_authors list is empty)
        assert mock_get_commit_info.call_count == 2

    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_commit_info")
    @pytest.mark.benchmark
    def test_commit_message_validator_empty_message_passes(
        self, mock_get_commit_info, mock_has_commits
    ):
        """CommitMessageValidator returns PASS when message is empty."""
        mock_has_commits.return_value = True
        mock_get_commit_info.side_effect = lambda fmt: {
            "s": "",
            "b": "",
            "an": "author",
        }.get(fmt, "")

        rule = ValidationRule(check="message", regex=r"^feat:")
        validator = CommitMessageValidator(rule)
        context = ValidationContext()

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_commit_message_validator_custom_pattern_jira(self):
        """Test CommitMessageValidator with a custom JIRA-style regex."""
        rule = ValidationRule(
            check="message",
            regex=r"^PROJ-\d+: .+",
        )
        validator = CommitMessageValidator(rule)

        # Valid JIRA-style message
        context = ValidationContext(stdin_text="PROJ-123: Fix login bug")
        result = validator.validate(context)
        assert result == ValidationResult.PASS

        # Invalid message (no issue key)
        context = ValidationContext(stdin_text="fix: login bug")
        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_commit_message_validator_custom_pattern_github_issue(self):
        """Test CommitMessageValidator with a GitHub issue reference pattern."""
        rule = ValidationRule(
            check="message",
            regex=r".+#\d+.*",
        )
        validator = CommitMessageValidator(rule)

        context = ValidationContext(stdin_text="Fix login bug #123")
        result = validator.validate(context)
        assert result == ValidationResult.PASS

        context = ValidationContext(stdin_text="Fix login bug")
        result = validator.validate(context)
        assert result == ValidationResult.FAIL


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
    @patch("commit_check.engine.get_git_config_value")
    @patch("commit_check.engine.get_commit_info")
    @pytest.mark.benchmark
    def test_branch_validator_ignored_author(
        self, mock_get_commit_info, mock_get_git_config_value, mock_get_branch_name
    ):
        """Test BranchValidator skips validation for ignored author."""
        mock_get_branch_name.return_value = "invalid-branch-name"
        mock_get_commit_info.return_value = "ignored"
        mock_get_git_config_value.return_value = ""
        rule = ValidationRule(check="branch", regex=r"^(feature|bugfix|hotfix)/.+")
        validator = BranchValidator(rule)
        config = {"branch": {"ignore_authors": ["ignored"]}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.SKIP

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
    def test_branch_validator_dependabot_branch_allowed(
        self, mock_get_branch_name, mock_has_commits
    ):
        """Test BranchValidator with dependabot branch (default type)."""
        mock_has_commits.return_value = True
        mock_get_branch_name.return_value = "dependabot/go_modules/go-deps-c57c3fe1e0"
        # Regex pattern that includes dependabot as a type prefix
        rule = ValidationRule(
            check="branch",
            regex=r"^(feature|bugfix|hotfix|dependabot)\/.+",
        )
        validator = BranchValidator(rule)
        config = {"branch": {"ignore_authors": []}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_branch_name")
    @pytest.mark.benchmark
    def test_branch_validator_renovate_branch_allowed(
        self, mock_get_branch_name, mock_has_commits
    ):
        """Test BranchValidator with renovate branch (default type)."""
        mock_has_commits.return_value = True
        mock_get_branch_name.return_value = "renovate/lodash-5.x"
        rule = ValidationRule(
            check="branch",
            regex=r"^(feature|bugfix|hotfix|dependabot|renovate)\/.+",
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

    @pytest.mark.benchmark
    def test_branch_ignored_author_uses_git_config_when_stdin(self):
        """
        Bug-fix guard (branch side): when stdin is piped, the last commit's
        author must NOT suppress branch-author skip logic.
        """
        rule = ValidationRule(check="branch", regex=r"^feature/")
        validator = BranchValidator(rule)

        config = {"branch": {"ignore_authors": ["pre-commit-ci[bot]"]}}
        context = ValidationContext(stdin_text="feature/valid-branch", config=config)

        with (
            patch(
                "commit_check.engine.get_commit_info", return_value="pre-commit-ci[bot]"
            ),
            patch(
                "commit_check.engine.get_git_config_value",
                return_value="Alice Developer",
            ),
        ):
            result = validator.validate(context)
        # Not skipped — Alice is not in ignore_authors for branches
        assert result == ValidationResult.PASS  # branch name is valid

    @pytest.mark.benchmark
    def test_branch_ignored_author_uses_commit_author_when_no_stdin(self):
        """
        Regression guard (branch side): when validating the current branch
        (no stdin), the check must use the last commit's author for
        ignore_authors, not the local git config.
        """
        rule = ValidationRule(check="branch", regex=r"^feature/")
        validator = BranchValidator(rule)

        config = {"branch": {"ignore_authors": ["dependabot[bot]"]}}
        context = ValidationContext(config=config)

        with (
            patch("commit_check.engine.has_commits", return_value=True),
            patch(
                "commit_check.engine.get_branch_name",
                return_value="dependabot/go-mod-upgrade",
            ),
            patch(
                "commit_check.engine.get_commit_info", return_value="dependabot[bot]"
            ),
            patch(
                "commit_check.engine.get_git_config_value",
                return_value="Alice Developer",
            ),
        ):
            result = validator.validate(context)
        # Skipped — the commit's author (dependabot[bot]) is in ignore_authors
        assert result == ValidationResult.SKIP


class TestAuthorValidator:
    @patch("commit_check.engine.has_commits")
    @patch(GIT_CONFIG_VALUE)
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
    @patch(GIT_CONFIG_VALUE)
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

    @patch("commit_check.engine.get_git_config_value")
    @patch("commit_check.engine.get_commit_info")
    @pytest.mark.benchmark
    def test_author_validator_ignored_author(
        self, mock_get_commit_info, mock_get_git_config_value
    ):
        """Test AuthorValidator skips validation for ignored author."""
        mock_get_commit_info.return_value = "ignored"
        mock_get_git_config_value.return_value = ""
        rule = ValidationRule(check="author_name", regex=r"^[A-Z][a-z]+ [A-Z][a-z]+$")
        validator = AuthorValidator(rule)
        config = {"commit": {"ignore_authors": ["ignored"]}}
        context = ValidationContext(config=config)
        result = validator.validate(context)
        assert result == ValidationResult.SKIP

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
            assert result == ValidationResult.SKIP

    @pytest.mark.benchmark
    def test_get_author_value_with_email_format(self):
        """Test _get_author_value with email format."""
        rule = ValidationRule(check="author_email")
        validator = AuthorValidator(rule)
        context = ValidationContext()

        with (
            patch(GIT_CONFIG_VALUE, return_value=""),
            patch(
                "commit_check.engine.get_commit_info", return_value="test@example.com"
            ),
        ):
            author_value = validator._get_author_value(context)
            assert author_value == "test@example.com"


class TestAuthorPatternConfig:
    """Tests for configurable author_name_pattern / author_email_pattern.

    Rules are built through RuleBuilder so the actual config resolution
    (custom pattern override + fallback to the built-in catalog regex) is
    exercised, not just an inline regex.
    """

    @staticmethod
    def _author_rule(commit_config, check):
        builder = RuleBuilder({"commit": commit_config})
        rules = builder.build_all_rules()
        return next(r for r in rules if r.check == check)

    @staticmethod
    def _validate(rule, author_value):
        validator = AuthorValidator(rule)
        with patch("commit_check.util._print_failure"):
            return validator.validate(ValidationContext(stdin_text=author_value))

    @pytest.mark.benchmark
    def test_custom_name_pattern_pass_and_fail(self):
        """A custom author_name_pattern accepts matches and rejects non-matches."""
        rule = self._author_rule(
            {"author_name_pattern": r"^[A-Z][a-z]+ [A-Z][a-z]+$"}, "author_name"
        )
        assert self._validate(rule, "Jane Doe") == ValidationResult.PASS
        assert self._validate(rule, "jane") == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_custom_email_pattern_enforces_domain(self):
        """A custom author_email_pattern can enforce a company domain."""
        rule = self._author_rule(
            {"author_email_pattern": r"^.+@company\.com$"}, "author_email"
        )
        assert self._validate(rule, "bob@company.com") == ValidationResult.PASS
        assert self._validate(rule, "bob@gmail.com") == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_default_name_pattern_uses_builtin_regex(self):
        """With no custom pattern, the built-in catalog regex still applies.

        Regression guard: an empty/omitted author_name_pattern must not disable
        the check — it should fall back to the shipped default so an invalid
        name is still rejected.
        """
        rule = self._author_rule({}, "author_name")
        assert self._validate(rule, "Jane Doe") == ValidationResult.PASS
        assert self._validate(rule, "12345 !!!") == ValidationResult.FAIL


class TestCommitTypeValidator:
    def test_supplied_empty_message_reaches_the_empty_commit_rule(self):
        """allow_empty_commits=False must actually reject an empty message.

        The early return on a falsy message used to make this unreachable, so
        the rejecting branch of _is_empty_commit_allowed was dead code. Patches
        get_commit_info to prove the verdict comes from the supplied message
        and not from the repository's own HEAD commit.
        """
        rule = ValidationRule(check="allow_empty_commits", value=False)
        validator = CommitTypeValidator(rule)
        with patch("commit_check.engine.get_commit_info") as mock_commit_info:
            mock_commit_info.return_value = "feat: something from git"
            result = validator.validate(
                ValidationContext(stdin_text="", no_banner=True)
            )
        assert result == ValidationResult.FAIL
        mock_commit_info.assert_not_called()

    def test_absent_message_still_skips_the_empty_commit_rule(self):
        """A message git never supplied is nothing to check, not a failure."""
        rule = ValidationRule(check="allow_empty_commits", value=False)
        validator = CommitTypeValidator(rule)
        with patch("commit_check.engine.get_commit_info", return_value=""):
            with patch("commit_check.engine.has_commits", return_value=True):
                result = validator.validate(ValidationContext(no_banner=True))
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_commit_type_validator_merge_commits(self):
        """Test CommitTypeValidator with merge commits."""
        rule = ValidationRule(check="allow_merge_commits", value=True)
        validator = CommitTypeValidator(rule)
        context = ValidationContext(stdin_text="Merge branch 'feature' into main")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_ignore_authors_records_resolved_author(self):
        """ignore_authors records the checked author identity, not the message."""
        rule = ValidationRule(check="ignore_authors", value=["ignored"])
        validator = CommitTypeValidator(rule)
        validator._collect_value = True
        context = ValidationContext(config={"commit": {"ignore_authors": ["ignored"]}})

        with patch("commit_check.engine.get_commit_info", return_value=""):
            with patch(GIT_CONFIG_VALUE, return_value="Jane Doe"):
                with patch("commit_check.engine.has_commits", return_value=True):
                    result = validator.validate(context)

        assert result == ValidationResult.PASS
        assert validator._checked_value == "Jane Doe"

    @pytest.mark.benchmark
    def test_ignore_authors_skipped_keeps_value_empty(self):
        """An ignored author skips the rule and leaves the value empty."""
        rule = ValidationRule(check="ignore_authors", value=["Jane Doe"])
        validator = CommitTypeValidator(rule)
        validator._collect_value = True
        context = ValidationContext(config={"commit": {"ignore_authors": ["Jane Doe"]}})

        with patch("commit_check.engine.get_commit_info", return_value="Jane Doe"):
            with patch("commit_check.engine.has_commits", return_value=True):
                result = validator.validate(context)

        assert result == ValidationResult.SKIP
        assert validator._checked_value == ""

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
    @staticmethod
    def _default_signoff_rule():
        """Build the require_signed_off_by rule from the default catalog regex.

        Unlike the tests that pass an inline regex, this exercises the actual
        default pattern shipped in rules_catalog, so a regression in that
        pattern is caught here.
        """
        builder = RuleBuilder({"commit": {"require_signed_off_by": True}})
        rules = builder.build_all_rules()
        return next(r for r in rules if r.check == "require_signed_off_by")

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
    def test_default_signoff_accepts_bot_name(self):
        """Default regex accepts a bracketed bot name such as dependabot[bot]."""
        validator = SignoffValidator(self._default_signoff_rule())
        context = ValidationContext(
            stdin_text=(
                "chore: bump dep\n\nSigned-off-by: dependabot[bot] <support@github.com>"
            )
        )

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_default_signoff_accepts_regular_name(self):
        """Default regex accepts a regular name and email signoff."""
        validator = SignoffValidator(self._default_signoff_rule())
        context = ValidationContext(
            stdin_text="feat: add feature\n\nSigned-off-by: John Doe <john@example.com>"
        )

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_default_signoff_rejects_missing_signoff(self):
        """Default regex rejects a message without any signoff trailer."""
        validator = SignoffValidator(self._default_signoff_rule())
        context = ValidationContext(stdin_text="feat: add feature")

        with patch("commit_check.util._print_failure"):
            result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @patch(GIT_CONFIG_VALUE)
    @patch("commit_check.engine.get_commit_info")
    @pytest.mark.benchmark
    def test_default_signoff_skips_ignored_author(
        self, mock_get_commit_info, mock_get_git_config_value
    ):
        """Signoff check is skipped when the author is in ignore_authors.

        A commit with no signoff would normally fail, but an ignored author
        (e.g. a bot) should bypass the signoff check just like every other
        commit check.
        """
        mock_get_commit_info.return_value = "dependabot[bot]"
        # Mock git config so author resolution falls back to the commit author
        # instead of the developer's real local user.name.
        mock_get_git_config_value.return_value = ""
        validator = SignoffValidator(self._default_signoff_rule())
        config = {"commit": {"ignore_authors": ["dependabot[bot]"]}}
        context = ValidationContext(stdin_text="chore: bump dep", config=config)

        result = validator.validate(context)
        assert result == ValidationResult.SKIP

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

    @pytest.mark.benchmark
    def test_validate_with_leading_blank_lines_and_body(self):
        """Test body validation with leading blank lines before body content.

        _get_commit_message() strips input before BodyValidator sees it, so
        leading blank lines are removed and this collapses to a single line
        with no separate subject/body it should FAIL.
        """
        rule = ValidationRule(check="require_body")
        validator = BodyValidator(rule)
        context = ValidationContext(stdin_text="\n\nbody content")

        with patch("commit_check.util._print_failure"):
            result = validator.validate(context)
            assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_validate_with_leading_blank_lines_no_body(self):
        """Test body validation with only leading blank lines and no content.

        After stripping, this becomes an empty message, which is treated as
        having no commit message at all — it should PASS.
        """
        rule = ValidationRule(check="require_body")
        validator = BodyValidator(rule)
        context = ValidationContext(stdin_text="\n\n")

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_validate_with_whitespace_only_message(self):
        """Test body validation with a whitespace-only message.

        After stripping, this becomes an empty message, same as the
        leading-blank-lines-only case — it should PASS.
        """
        rule = ValidationRule(check="require_body")
        validator = BodyValidator(rule)
        context = ValidationContext(stdin_text=" \n ")

        result = validator.validate(context)
        assert result == ValidationResult.PASS


class TestMergeBaseValidator:
    @patch("commit_check.engine.git_merge_base")
    @pytest.mark.benchmark
    def test_merge_base_validator_valid(self, mock_git_merge_base):
        """Test MergeBaseValidator with valid merge base.

        Patched on commit_check.engine, not commit_check.util: the engine
        imported the name directly, so patching the util module rebound
        nothing and these tests were running real git against the checkout
        they happened to be executed in.
        """
        mock_git_merge_base.return_value = 0

        # With no regex, validate() returns PASS at the "no target configured"
        # exit without ever calling git_merge_base — the assertion below would
        # hold no matter what the mock returned. Give it a target so the
        # merge-base path actually runs.
        rule = ValidationRule(check="merge_base", regex=r"^main$")
        validator = MergeBaseValidator(rule)
        context = ValidationContext()

        with (
            patch.object(validator, "_find_target_branch", return_value="origin/main"),
            patch("commit_check.engine.get_branch_name", return_value="feature/test"),
            patch("commit_check.engine.has_commits", return_value=True),
        ):
            result = validator.validate(context)
        assert result == ValidationResult.PASS
        mock_git_merge_base.assert_called_once_with("origin/main", "feature/test")

    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_branch_name")
    @patch("commit_check.engine.git_merge_base")
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
            assert result == ValidationResult.SKIP  # the rule never ran

    # ------------------------------------------------------------------ #
    #  _find_target_branch —— unit tests for the new impl
    # ------------------------------------------------------------------ #

    @patch("subprocess.run")
    def test_find_target_branch_local_found(self, mock_run):
        """Local branch exists: returns the stripped branch name."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        validator = MergeBaseValidator(ValidationRule(check="merge_base"))
        result = validator._find_target_branch("^main$")
        assert result == "main"
        # First call: local branch verification
        assert mock_run.call_args_list[0][0][0][:4] == [
            "git",
            "rev-parse",
            "--verify",
            "refs/heads/main",
        ]

    @patch("subprocess.run")
    def test_find_target_branch_local_missing_remote_found(self, mock_run):
        """Local missing, remote tracking exists: returns the remote-qualified name.

        Qualified, not bare: the caller feeds this straight to ``git merge-base
        --is-ancestor``, and a checkout holding only ``origin/develop`` cannot
        resolve ``develop``. Git exits 128 there, which the validator reports as
        "not rebased onto target branch" — a clean branch failing for a name it
        could not look up.
        """
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, []),  # local fails
            subprocess.CompletedProcess(args=[], returncode=0),  # remote succeeds
        ]
        validator = MergeBaseValidator(ValidationRule(check="merge_base"))
        result = validator._find_target_branch("develop")
        assert result == "origin/develop"
        assert mock_run.call_args_list[1][0][0][:5] == [
            "git",
            "rev-parse",
            "--verify",
            "refs/remotes/origin/develop",
        ]

    @patch("subprocess.run")
    def test_find_target_branch_not_found(self, mock_run):
        """Neither local nor remote exists: returns None."""
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, []),
            subprocess.CalledProcessError(1, []),
        ]
        validator = MergeBaseValidator(ValidationRule(check="merge_base"))
        result = validator._find_target_branch("nonexistent-branch")
        assert result is None

    def test_merge_base_against_a_real_pull_request_shaped_checkout(self, tmp_path):
        """A branch based on origin/main passes when no local main exists.

        Mocked subprocess is what let this through: every call was asserted
        against the arguments the code happened to pass, so a target name git
        could not resolve looked correct. This drives real git instead.
        """
        from commit_check.util import git_merge_base

        clone, git = _pull_request_shaped_clone(tmp_path)
        git("branch", "-q", "-D", "main", cwd=clone)

        cwd = os.getcwd()
        try:
            os.chdir(clone)
            validator = MergeBaseValidator(ValidationRule(check="merge_base"))
            target = validator._find_target_branch("main")
            assert target == "origin/main"
            # The point of the qualification: this is what the caller runs.
            assert git_merge_base(target, "feat/work") == 0
        finally:
            os.chdir(cwd)

    def test_merge_base_on_a_detached_checkout_with_no_local_branch(self, tmp_path):
        """A detached checkout passes when the branch name resolves to nothing.

        The other half of the same mistake: get_branch_name() falls back to
        GITHUB_HEAD_REF, so on a CI checkout of a pull request it reports a
        branch that was never created locally. git exits 128 on the name, and
        128 was read as "not an ancestor" rather than "could not look that up".
        """
        clone, git = _pull_request_shaped_clone(tmp_path)
        git("checkout", "-q", "--detach", "HEAD", cwd=clone)
        git("branch", "-q", "-D", "main", cwd=clone)
        git("branch", "-q", "-D", "feat/work", cwd=clone)

        cwd = os.getcwd()
        try:
            os.chdir(clone)
            with patch.dict(os.environ, {"GITHUB_HEAD_REF": "feat/never-created"}):
                validator = MergeBaseValidator(
                    ValidationRule(check="merge_base", regex="main")
                )
                result = validator.validate(ValidationContext())
        finally:
            os.chdir(cwd)
        assert result == ValidationResult.PASS

    def test_merge_base_fails_a_diverged_branch_on_a_merge_ref_checkout(self, tmp_path):
        """A branch that is NOT rebased must fail, even on a merge-ref checkout.

        On a pull_request event the runner checks out GitHub's synthetic merge
        commit, whose first parent IS the target tip — so answering the
        ancestry question from HEAD passes every branch, rebased or not. The
        branch must be resolved through its remote-tracking ref instead; this
        test pins that, and fails if the HEAD fallback is consulted first.
        """
        clone, _ = _diverged_merge_ref_clone(tmp_path)
        assert _validate_merge_base(clone) == ValidationResult.FAIL

    def test_merge_base_fails_a_diverged_branch_with_no_remote_ref(self, tmp_path):
        """The same diverged branch must still fail when even the remote ref is
        gone, which is where the fallback chain runs out of names.

        Measured in this shape: origin/main vs feat/work is 128, vs
        origin/feat/work is 128, and vs HEAD is 0 -- so falling through to HEAD
        would pass a branch that is genuinely behind. HEAD's *second* parent is
        the pull request head and answers 1, the truth.
        """
        clone, git = _diverged_merge_ref_clone(tmp_path)
        # Leave the branch unresolvable under every name.
        git("update-ref", "-d", "refs/remotes/origin/feat/work", cwd=clone)
        assert _validate_merge_base(clone) == ValidationResult.FAIL

    @patch("subprocess.run")
    def test_find_target_branch_empty_pattern(self, mock_run):
        """Empty or anchor-only pattern: returns None without calling subprocess."""
        validator = MergeBaseValidator(ValidationRule(check="merge_base"))
        result = validator._find_target_branch("")
        assert result is None
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_find_target_branch_plain_name(self, mock_run):
        """Plain branch name (no regex anchors) works correctly."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        validator = MergeBaseValidator(ValidationRule(check="merge_base"))
        result = validator._find_target_branch("main")
        assert result == "main"
        assert mock_run.call_args_list[0][0][0][3] == "refs/heads/main"


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
    def test_validate_all_detailed_reports_value_on_pass(self):
        """Passed checks still report the concrete value that was checked."""
        rules = [
            ValidationRule(check="message", regex=r"^feat:"),
            ValidationRule(check="subject_imperative", regex=r""),
        ]
        engine = ValidationEngine(rules)
        context = ValidationContext(stdin_text="feat: add feature")

        outcomes = engine.validate_all_detailed(context)
        assert len(outcomes) == 2
        assert all(o.status == "pass" for o in outcomes)
        by_check = {o.check: o for o in outcomes}
        assert by_check["message"].value == "feat: add feature"
        assert by_check["subject_imperative"].value == "feat: add feature"

    @pytest.mark.benchmark
    def test_validate_all_detailed_author_reports_author_name(self):
        """Author check reports the checked identity even when it passes."""
        rules = [ValidationRule(check="author_name", regex=r"^Jane")]
        engine = ValidationEngine(rules)

        with patch(GIT_CONFIG_VALUE, return_value="Jane Doe"):
            outcomes = engine.validate_all_detailed(ValidationContext())

        assert outcomes[0].status == "pass"
        assert outcomes[0].value == "Jane Doe"

    @pytest.mark.benchmark
    def test_validate_all_detailed_branch_reports_branch_name(self):
        """Branch check reports the branch name even when it passes."""
        rules = [ValidationRule(check="branch", regex=r"^feature/")]
        engine = ValidationEngine(rules)
        context = ValidationContext(stdin_text="feature/add-login")

        outcomes = engine.validate_all_detailed(context)
        assert outcomes[0].status == "pass"
        assert outcomes[0].value == "feature/add-login"

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
            "ai_attribution": AiAttributionValidator,
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

    @patch("commit_check.engine.has_commits")
    @patch("commit_check.engine.get_commit_info")
    @pytest.mark.benchmark
    def test_validate_empty_subject_passes(
        self, mock_get_commit_info, mock_has_commits
    ):
        """SubjectValidator returns PASS when subject is empty."""
        mock_has_commits.return_value = True
        mock_get_commit_info.side_effect = lambda fmt: {
            "s": "",
            "b": "",
            "an": "author",
        }.get(fmt, "")

        rule = ValidationRule(check="subject_capitalized")
        validator = SubjectCapitalizationValidator(rule)
        context = ValidationContext()

        result = validator.validate(context)
        assert result == ValidationResult.PASS


class TestSubjectImperativeValidator:
    """Test SubjectImperativeValidator edge cases."""

    @pytest.mark.benchmark
    @pytest.mark.parametrize(
        "subject",
        [
            "fix: backport the patch",
            "chore: comment out the entry",
            "docs: embed the example",
            "build: polyfill the API",
            "docs: revamp the profile",
            "chore: vendor the dependency",
        ],
    )
    def test_validate_with_common_imperative_subjects(self, subject):
        """Common imperative verbs pass subject validation."""
        rule = ValidationRule(check="subject_imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text=subject)

        result = validator.validate(context)

        assert result == ValidationResult.PASS

    @pytest.mark.parametrize(
        "subject",
        [
            # Rejected before the list was extended, every one of them written
            # in correct imperative mood.
            "feat: settle the report format",
            "fix: avoid a second lookup",
            "docs: clarify the default value",
            "refactor: factor out the helper",
            "chore: teach the parser about tabs",
            "fix: free the buffer on the error path",
            "refactor: inline the wrapper",
            "fix: restore the previous behaviour",
            "chore: retire the legacy flag",
            # British spelling is not a mistake. The last pair is the case the
            # file used to get wrong most often: the -ize form was listed and
            # the -ise one was not, so only half of a spelling pair worked.
            "refactor: normalise the path separators",
            "chore: prioritise the queue",
            "feat: customise the template",
            "feat: customize the template",
        ],
    )
    def test_correct_imperative_subjects_are_not_rejected(self, subject):
        """Words a contributor would have had to reword around must pass.

        A whitelist can only approximate "is this an imperative verb", and the
        cost of a gap falls on someone who wrote the subject correctly.
        """
        rule = ValidationRule(check="subject_imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text=subject)

        assert validator.validate(context) == ValidationResult.PASS

    @pytest.mark.parametrize(
        "subject",
        [
            "fix: updated the parser",
            "feat: adding a new flag",
            "fix: fixes the crash",
            "chore: removed the dead code",
        ],
    )
    def test_wrong_verb_forms_still_fail(self, subject):
        """Extending the list must not weaken what the rule is there to catch."""
        rule = ValidationRule(check="subject_imperative")
        validator = SubjectImperativeValidator(rule)
        context = ValidationContext(stdin_text=subject)

        assert validator.validate(context) == ValidationResult.FAIL

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
            regex=CONVENTIONAL_COMMIT_REGEX,
            error=BAD_COMMIT_MSG,
            suggest=USE_CONVENTIONAL_FORMAT,
        )
        validator = CommitMessageValidator(rule)

        message = "Update README\n\nCo-authored-by: coderabbitai[bot] <bot@example.com>"
        config = {"commit": {"ignore_authors": ["coderabbitai[bot]"]}}
        context = ValidationContext(stdin_text=message, config=config)

        with patch("commit_check.engine.get_commit_info", return_value="other-author"):
            result = validator.validate(context)
        assert result == ValidationResult.SKIP

    @pytest.mark.benchmark
    def test_co_author_not_in_ignore_list_does_not_skip(self):
        """Test that co-author not in ignore list does not bypass validation."""
        rule = ValidationRule(
            check="message",
            regex=CONVENTIONAL_COMMIT_REGEX,
            error=BAD_COMMIT_MSG,
            suggest=USE_CONVENTIONAL_FORMAT,
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
            regex=CONVENTIONAL_COMMIT_REGEX,
            error=BAD_COMMIT_MSG,
            suggest=USE_CONVENTIONAL_FORMAT,
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
            assert result == ValidationResult.SKIP
        finally:
            os.unlink(commit_file)

    @pytest.mark.benchmark
    def test_author_in_ignore_list_uses_git_config_when_stdin(self):
        """
        Bug-fix guard: when stdin is piped, the last commit's author
        (e.g. a bot in the ignore list) must NOT suppress validation.
        The check should use the local git config user.name instead.
        """
        rule = ValidationRule(
            check="message",
            regex=CONVENTIONAL_COMMIT_REGEX,
            error=BAD_COMMIT_MSG,
            suggest=USE_CONVENTIONAL_FORMAT,
        )
        validator = CommitMessageValidator(rule)

        # HEAD author is "pre-commit-ci[bot]" (in ignore list)
        # but local git config user.name is a human (not ignored)
        # stdin is a proper conventional commit — validation should run.
        message = "fix: resolve edge case in parser"
        config = {"commit": {"ignore_authors": ["pre-commit-ci[bot]"]}}
        context = ValidationContext(stdin_text=message, config=config)

        with (
            patch(
                "commit_check.engine.get_commit_info", return_value="pre-commit-ci[bot]"
            ),
            patch(
                "commit_check.engine.get_git_config_value",
                return_value="Alice Developer",
            ),
        ):
            result = validator.validate(context)
        # Not skipped — Alice is not in ignore_authors, so validation runs
        assert result == ValidationResult.PASS  # message is valid

    @pytest.mark.benchmark
    def test_author_in_ignore_list_uses_commit_author_when_no_stdin(self):
        """
        Regression guard: when validating an existing commit (no stdin),
        the check must use the commit's own author, not the local git config.
        A bot commit should still be skipped when its author is ignore_authors,
        even if user.name is a human.
        """
        rule = ValidationRule(
            check="message",
            regex=CONVENTIONAL_COMMIT_REGEX,
            error=BAD_COMMIT_MSG,
            suggest=USE_CONVENTIONAL_FORMAT,
        )
        validator = CommitMessageValidator(rule)

        # HEAD author is "dependabot[bot]" (in ignore list)
        # local git config user.name is a human (not ignored)
        # no stdin — validating the last commit as-is.
        config = {"commit": {"ignore_authors": ["dependabot[bot]"]}}
        context = ValidationContext(config=config)

        with (
            patch("commit_check.engine.has_commits", return_value=True),
            patch(
                "commit_check.engine.get_commit_info", return_value="dependabot[bot]"
            ),
            patch(
                "commit_check.engine.get_git_config_value",
                return_value="Alice Developer",
            ),
        ):
            result = validator.validate(context)
        # Skipped — the commit's author (dependabot[bot]) is in ignore_authors
        assert result == ValidationResult.SKIP

    @pytest.mark.benchmark
    def test_author_in_ignore_list_falls_back_to_git_config_when_commit_info_empty(
        self,
    ):
        """
        Coverage guard: when no stdin/commit_file and get_commit_info("an")
        returns empty, _resolve_current_author must fall back to
        get_git_config_value("user.name").
        """
        rule = ValidationRule(
            check="message",
            regex=CONVENTIONAL_COMMIT_REGEX,
            error=BAD_COMMIT_MSG,
            suggest=USE_CONVENTIONAL_FORMAT,
        )
        validator = CommitMessageValidator(rule)

        config = {"commit": {"ignore_authors": ["Developer Bot"]}}
        context = ValidationContext(config=config)

        with (
            patch("commit_check.engine.has_commits", return_value=True),
            patch("commit_check.engine.get_commit_info", return_value=""),
            patch(
                "commit_check.engine.get_git_config_value",
                return_value="Developer Bot",
            ),
        ):
            result = validator.validate(context)
        # Skipped — fallback author (Developer Bot) is in ignore_authors
        assert result == ValidationResult.SKIP


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
                GIT_CONFIG_VALUE,
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
            patch(GIT_CONFIG_VALUE, return_value=""),
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
                GIT_CONFIG_VALUE,
                return_value="user@example.com",
            ),
        ):
            result = validator.validate(context)
        assert result == ValidationResult.PASS


class TestForcePushValidator:
    """Tests for the ForcePushValidator class."""

    ZERO_SHA = "0000000000000000000000000000000000000000"

    def _make_rule(self):
        return ValidationRule(
            check="no_force_push",
            error="Force push is not allowed",
            suggest="Use a normal push instead of --force or --force-with-lease",
            value=False,
        )

    @pytest.mark.benchmark
    def test_no_stdin_skips_validation(self):
        """Validator passes when no stdin is provided (not a pre-push context)."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        context = ValidationContext()  # stdin_text=None

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_multiple_push_refs_accumulate_checked_value(self):
        """Every validated ref pair is preserved, not overwritten."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        stdin = (
            "refs/heads/main deadbeef refs/heads/main abc123\n"
            "refs/heads/feature/x deadbeef refs/heads/feature/x "
            f"{self.ZERO_SHA}\n"
        )
        context = ValidationContext(stdin_text=stdin)

        with patch("commit_check.engine.git_merge_base", return_value=0):
            result = validator.validate(context)

        assert result == ValidationResult.PASS
        assert validator._checked_value == (
            "refs/heads/main -> refs/heads/main\n"
            "refs/heads/feature/x -> refs/heads/feature/x"
        )

    @pytest.mark.benchmark
    def test_no_stdin_with_upstream_fallback_passes_without_upstream(self):
        """Standalone mode passes when the current branch has no upstream."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        context = ValidationContext(push_upstream_fallback=True)

        with patch("commit_check.engine.get_upstream_branch", return_value=""):
            result = validator.validate(context)

        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_no_stdin_with_upstream_fallback_passes_fast_forward(self):
        """Standalone mode passes when upstream is an ancestor of HEAD."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        context = ValidationContext(push_upstream_fallback=True)

        with patch(
            "commit_check.engine.get_upstream_branch", return_value="origin/main"
        ):
            with patch(
                "commit_check.engine.get_upstream_remote_sha", return_value="abc123"
            ):
                with patch("commit_check.engine.git_merge_base", return_value=0):
                    result = validator.validate(context)

        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_upstream_fallback_text_mode_skips_branch_lookup(self):
        """Text mode does not pay for the extra branch-name lookup."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        context = ValidationContext(push_upstream_fallback=True)

        with patch(
            "commit_check.engine.get_upstream_branch", return_value="origin/main"
        ):
            with patch(
                "commit_check.engine.get_upstream_remote_sha", return_value="abc123"
            ):
                with patch("commit_check.engine.git_merge_base", return_value=0):
                    with patch("commit_check.engine.get_branch_name") as mock_branch:
                        result = validator.validate(context)

        assert result == ValidationResult.PASS
        mock_branch.assert_not_called()

    @pytest.mark.benchmark
    def test_upstream_fallback_structured_mode_records_value(self):
        """Structured mode records branch -> upstream as the checked value."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        validator._collect_value = True
        context = ValidationContext(push_upstream_fallback=True)

        with patch(
            "commit_check.engine.get_upstream_branch", return_value="origin/main"
        ):
            with patch(
                "commit_check.engine.get_upstream_remote_sha", return_value="abc123"
            ):
                with patch("commit_check.engine.git_merge_base", return_value=0):
                    with patch(
                        "commit_check.engine.get_branch_name", return_value="main"
                    ):
                        result = validator.validate(context)

        assert result == ValidationResult.PASS
        assert validator._checked_value == "main -> origin/main"

    @pytest.mark.benchmark
    def test_no_stdin_with_upstream_fallback_uses_tracking_ref_when_remote_sha_missing(
        self,
    ):
        """Standalone mode uses local tracking ref if ls-remote lookup fails."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        context = ValidationContext(push_upstream_fallback=True)

        with patch(
            "commit_check.engine.get_upstream_branch", return_value="origin/main"
        ):
            with patch("commit_check.engine.get_upstream_remote_sha", return_value=""):
                with patch(
                    "commit_check.engine.git_merge_base", return_value=0
                ) as mock_merge:
                    result = validator.validate(context)

        mock_merge.assert_called_once_with("origin/main", "HEAD")
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_no_stdin_with_upstream_fallback_blocks_force_push(self):
        """Standalone mode fails when pushing HEAD to upstream requires force."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        context = ValidationContext(push_upstream_fallback=True)

        with patch(
            "commit_check.engine.get_upstream_branch", return_value="origin/main"
        ):
            with patch(
                "commit_check.engine.get_upstream_remote_sha", return_value="deadbeef"
            ):
                with patch("commit_check.engine.get_branch_name", return_value="main"):
                    with patch(
                        "commit_check.engine.git_merge_base", return_value=1
                    ) as mock_merge:
                        with patch("commit_check.util._print_failure"):
                            result = validator.validate(context)

        mock_merge.assert_called_once_with("deadbeef", "HEAD")
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_no_stdin_with_upstream_fallback_fetches_remote_commit_when_needed(self):
        """Standalone mode fetches the upstream commit if not local yet."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        context = ValidationContext(push_upstream_fallback=True)

        with patch(
            "commit_check.engine.get_upstream_branch", return_value="origin/main"
        ):
            with patch(
                "commit_check.engine.get_upstream_remote_sha", return_value="deadbeef"
            ):
                with patch("commit_check.engine.get_branch_name", return_value="main"):
                    with patch(
                        "commit_check.engine.git_merge_base", side_effect=[128, 1]
                    ) as mock_merge:
                        with patch(
                            "commit_check.engine.fetch_upstream_ref", return_value=True
                        ) as mock_fetch:
                            with patch("commit_check.util._print_failure"):
                                result = validator.validate(context)

        mock_fetch.assert_called_once_with("origin/main")
        assert mock_merge.call_count == 2
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_new_branch_push_is_allowed(self):
        """A push to a new (non-existent) remote branch is not a force push."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        push_info = (
            f"refs/heads/feature/new abc123 refs/heads/feature/new {self.ZERO_SHA}"
        )
        context = ValidationContext(stdin_text=push_info)

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_fast_forward_push_is_allowed(self):
        """A normal fast-forward push (remote is ancestor of local) is allowed."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        push_info = "refs/heads/main abc123 refs/heads/main def456"
        context = ValidationContext(stdin_text=push_info)

        with patch("commit_check.engine.git_merge_base", return_value=0):
            result = validator.validate(context)

        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_force_push_is_blocked(self):
        """A force push (remote is NOT ancestor of local) is blocked."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        push_info = "refs/heads/main abc123 refs/heads/main def456"
        context = ValidationContext(stdin_text=push_info)

        with patch("commit_check.engine.git_merge_base", return_value=1):
            with patch("commit_check.util._print_failure"):
                result = validator.validate(context)

        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_git_error_allows_push(self):
        """When git cannot determine ancestry after fetch failure, push is allowed."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        push_info = "refs/heads/main abc123 refs/heads/main def456"
        context = ValidationContext(stdin_text=push_info)

        with patch("commit_check.engine.git_merge_base", return_value=128):
            with patch(FETCH_REMOTE_REF, return_value=False) as mock_fetch:
                with patch(GET_GIT_REMOTES, return_value=["origin"]):
                    with patch(
                        "commit_check.engine.get_upstream_branch", return_value=""
                    ):
                        result = validator.validate(context)

        mock_fetch.assert_called_once_with("origin", REFS_HEADS_MAIN)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_missing_remote_sha_is_fetched_then_force_push_is_blocked(self):
        """A missing remote SHA is fetched before deciding the push is safe."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        push_info = "refs/heads/main abc123 refs/heads/main def456"
        context = ValidationContext(stdin_text=push_info)

        with patch(
            "commit_check.engine.git_merge_base", side_effect=[128, 1]
        ) as mock_merge:
            with patch("commit_check.engine.get_upstream_branch", return_value=""):
                with patch(GET_GIT_REMOTES, return_value=["origin"]):
                    with patch(FETCH_REMOTE_REF, return_value=True) as mock_fetch:
                        with patch("commit_check.util._print_failure"):
                            result = validator.validate(context)

        assert mock_merge.call_count == 2
        mock_fetch.assert_called_once_with("origin", REFS_HEADS_MAIN)
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_missing_remote_sha_fetch_prefers_matching_upstream_remote(self):
        """The matching upstream remote is fetched before other remotes."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        push_info = "refs/heads/main abc123 refs/heads/main def456"
        context = ValidationContext(stdin_text=push_info)

        with patch("commit_check.engine.git_merge_base", side_effect=[128, 0]):
            with patch(
                "commit_check.engine.get_upstream_branch", return_value="upstream/main"
            ):
                with patch(
                    GET_GIT_REMOTES,
                    return_value=["origin", "upstream"],
                ):
                    with patch(FETCH_REMOTE_REF, return_value=True) as mock_fetch:
                        result = validator.validate(context)

        mock_fetch.assert_called_once_with("upstream", REFS_HEADS_MAIN)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_missing_remote_sha_tries_next_remote_until_resolved(self):
        """Fetching one remote is not enough if it did not contain the SHA."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        push_info = "refs/heads/main abc123 refs/heads/main def456"
        context = ValidationContext(stdin_text=push_info)

        with patch(
            "commit_check.engine.git_merge_base", side_effect=[128, 128, 1]
        ) as mock_merge:
            with patch("commit_check.engine.get_upstream_branch", return_value=""):
                with patch(
                    GET_GIT_REMOTES,
                    return_value=["origin", "upstream"],
                ):
                    with patch(FETCH_REMOTE_REF, return_value=True) as mock_fetch:
                        with patch("commit_check.util._print_failure"):
                            result = validator.validate(context)

        assert mock_merge.call_count == 3
        assert [call.args for call in mock_fetch.call_args_list] == [
            ("origin", REFS_HEADS_MAIN),
            ("upstream", REFS_HEADS_MAIN),
        ]
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_empty_lines_in_stdin_are_skipped(self):
        """Empty lines in push info do not cause errors."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        push_info = "\n\nrefs/heads/main abc123 refs/heads/main def456\n\n"
        context = ValidationContext(stdin_text=push_info)

        with patch("commit_check.engine.git_merge_base", return_value=0):
            result = validator.validate(context)

        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_malformed_push_line_is_skipped(self):
        """Lines that do not have 4 fields are silently skipped."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        push_info = "only two fields"
        context = ValidationContext(stdin_text=push_info)

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_multiple_refs_one_force_push_blocks(self):
        """If any pushed ref is a force push, the whole check fails."""
        rule = self._make_rule()
        validator = ForcePushValidator(rule)
        push_info = (
            f"refs/heads/feature/ok abc1 refs/heads/feature/ok {self.ZERO_SHA}\n"
            "refs/heads/main abc2 refs/heads/main def2"
        )
        context = ValidationContext(stdin_text=push_info)

        # Allow new branch, but force push on second line
        def side_effect(remote_sha, local_sha):
            if remote_sha == self.ZERO_SHA:
                return 0
            return 1

        with patch("commit_check.engine.git_merge_base", side_effect=side_effect):
            with patch("commit_check.util._print_failure"):
                result = validator.validate(context)

        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_validation_engine_includes_force_push_validator(self):
        """ValidationEngine maps 'no_force_push' to ForcePushValidator."""
        assert "no_force_push" in ValidationEngine.VALIDATOR_MAP
        assert ValidationEngine.VALIDATOR_MAP["no_force_push"] is ForcePushValidator

    @pytest.mark.benchmark
    def test_validation_context_push_upstream_fallback(self):
        """ValidationContext supports push_upstream_fallback field."""
        ctx = ValidationContext(push_upstream_fallback=True)
        assert ctx.push_upstream_fallback is True
        ctx2 = ValidationContext()
        assert ctx2.push_upstream_fallback is False


class TestAiAttributionValidator:
    """Tests for AiAttributionValidator."""

    @pytest.mark.benchmark
    def test_ignore_policy_always_passes(self):
        """ignore policy skips all validation."""
        rule = ValidationRule(
            check="ai_attribution",
            value="ignore",
        )
        validator = AiAttributionValidator(rule)
        message = "feat: add feature\n\nCo-authored-by: Claude <noreply@anthropic.com>"
        context = ValidationContext(stdin_text=message)
        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_forbid_policy_rejects_ai_commit(self):
        """forbid policy rejects commits with AI signatures."""
        rule = ValidationRule(
            check="ai_attribution",
            value="forbid",
        )
        validator = AiAttributionValidator(rule)
        message = "feat: add feature\n\nCo-authored-by: Claude <noreply@anthropic.com>"
        context = ValidationContext(stdin_text=message)
        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_forbid_policy_allows_clean_commit(self):
        """forbid policy allows commits without AI signatures."""
        rule = ValidationRule(
            check="ai_attribution",
            value="forbid",
        )
        validator = AiAttributionValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature by hand")
        result = validator.validate(context)
        assert result == ValidationResult.PASS

    @pytest.mark.benchmark
    def test_forbid_policy_clean_commit_records_message(self):
        """forbid policy records the scanned message when no signature is found."""
        rule = ValidationRule(
            check="ai_attribution",
            value="forbid",
        )
        validator = AiAttributionValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature by hand")
        result = validator.validate(context)
        assert result == ValidationResult.PASS
        assert validator._checked_value == "feat: add feature by hand"

    @pytest.mark.benchmark
    def test_ignore_policy_records_no_value(self):
        """ignore policy is a no-op and records no checked value."""
        rule = ValidationRule(
            check="ai_attribution",
            value="ignore",
        )
        validator = AiAttributionValidator(rule)
        context = ValidationContext(stdin_text="feat: add feature")
        result = validator.validate(context)
        assert result == ValidationResult.PASS
        assert validator._checked_value == ""

    @pytest.mark.benchmark
    def test_forbid_policy_multiple_tools(self):
        """forbid rejects commits with multiple AI tools."""
        rule = ValidationRule(
            check="ai_attribution",
            value="forbid",
        )
        validator = AiAttributionValidator(rule)
        message = (
            "feat: implement feature\n\n"
            "Co-authored-by: Claude <noreply@anthropic.com>\n"
            "Co-authored-by: Copilot <noreply@github.com>"
        )
        context = ValidationContext(stdin_text=message)
        result = validator.validate(context)
        assert result == ValidationResult.FAIL

    @pytest.mark.benchmark
    def test_skip_when_author_ignored(self):
        """Validation is skipped when author is in ignore list."""
        rule = ValidationRule(
            check="ai_attribution",
            value="forbid",
        )
        validator = AiAttributionValidator(rule)
        message = "feat: add feature\n\nCo-authored-by: Claude"
        config = {"commit": {"ignore_authors": ["bot-user"]}}
        context = ValidationContext(stdin_text=message, config=config)

        with (
            patch("commit_check.engine.get_commit_info", return_value="bot-user"),
            patch("commit_check.engine.get_git_config_value", return_value=""),
        ):
            result = validator.validate(context)
        assert result == ValidationResult.SKIP  # the rule never ran

    @pytest.mark.benchmark
    def test_empty_message_passes(self):
        """Empty message passes validation."""
        rule = ValidationRule(
            check="ai_attribution",
            value="forbid",
        )
        validator = AiAttributionValidator(rule)
        context = ValidationContext(stdin_text="")
        result = validator.validate(context)
        assert result == ValidationResult.PASS

        result = validator.validate(context)
        assert result == ValidationResult.PASS

    def test_empty_message_is_not_read_from_git(self):
        """An empty stdin_text must not fall through to the HEAD commit.

        The assertion above only holds while the checkout's own HEAD carries no
        AI trailers, so it passed on pull request runs — where HEAD is GitHub's
        synthetic merge commit with an empty body — and went red on main the
        moment a commit with a Co-authored-by trailer landed. This pins the
        behaviour itself, independent of whatever the repository last
        committed.
        """
        with patch("commit_check.engine.get_commit_info") as mock_commit_info:
            mock_commit_info.return_value = "Co-authored-by: Claude <n@example.com>"
            body = AiAttributionValidator._get_commit_body(
                ValidationContext(stdin_text="")
            )
        assert body == ""
        mock_commit_info.assert_not_called()
