"""CC305: paths a commit attributed to an AI tool may not change."""

import os
import subprocess

import pytest

from commit_check.engine import (
    FilesValidator,
    ValidationContext,
    ValidationEngine,
    ValidationResult,
    _ai_tool_behind,
)
from commit_check.main import main
from commit_check.rule_builder import RuleBuilder, ValidationRule

PATTERNS = [".github/workflows/*", "CODEOWNERS", "*.lock"]
PERSON = ("Jane Dev", "jane@example.com")
BOT = ("copilot-swe-agent[bot]", "198982749+Copilot@users.noreply.github.com")
CO_AUTHOR = "Co-Authored-By: Claude <noreply@anthropic.com>"
ZERO = "0" * 40


def _validator(patterns=PATTERNS, allowed=None):
    rule = ValidationRule(check="ai_file_pattern", value=patterns, allowed=allowed)
    validator = FilesValidator(rule)
    validator._suppress_output = True
    return validator


@pytest.fixture
def commits(mocker):
    """Stand-in history: ``commits[rev] = (author, message, changed paths)``."""
    history = {}
    mocker.patch(
        "commit_check.engine.get_commit_authorship",
        side_effect=lambda rev: (
            None if history[rev][0] is None else (*history[rev][0], history[rev][1])
        ),
    )
    history["paths_read"] = mocker.patch(
        "commit_check.engine.get_commit_changed_paths",
        side_effect=lambda rev: history[rev][2],
    )
    return history


class TestWhoACommitIsAttributedTo:
    @pytest.mark.parametrize(
        ("name", "email", "message", "tool"),
        [
            (*PERSON, "fix: typo", None),
            (*PERSON, "fix: typo\n\nSigned-off-by: Jane Dev <jane@example.com>", None),
            (*PERSON, f"fix: typo\n\n{CO_AUTHOR}", "Claude Code"),
            (*PERSON, "fix: typo\n\nAssisted-by: Cursor", "Cursor"),
            (
                *PERSON,
                "fix: typo\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)",
                "Claude Code",
            ),
            (*BOT, "fix: typo", "GitHub Copilot"),
            # The author outranks what the message says.
            (*BOT, "fix: typo\n\nAssisted-by: Cursor", "GitHub Copilot"),
        ],
    )
    def test_author_then_message(self, name, email, message, tool):
        assert _ai_tool_behind(name, email, message, ["Assisted-by"]) == tool

    def test_a_disclosure_counts_under_the_trailers_the_project_accepts(self):
        message = "fix: typo\n\nAI-assistant: SomeNewAgent 1.2"
        assert _ai_tool_behind(*PERSON, message, ["Assisted-by"]) is None
        assert (
            _ai_tool_behind(*PERSON, message, ["Assisted-by", "AI-assistant"])
            == "SomeNewAgent 1.2"
        )

    def test_an_empty_disclosure_names_no_tool(self):
        assert (
            _ai_tool_behind(*PERSON, "fix: typo\n\nAssisted-by:", ["Assisted-by"])
            is None
        )


class TestAiFilePattern:
    def test_a_person_may_change_the_paths(self, commits):
        commits["HEAD"] = (PERSON, "ci: tweak", [".github/workflows/ci.yml"])
        validator = _validator()
        assert validator.validate(ValidationContext()) == ValidationResult.PASS
        assert validator._checked_value == "no commit attributed to an AI tool"
        commits["paths_read"].assert_not_called()

    def test_a_commit_with_an_ai_co_author_may_not(self, commits):
        commits["HEAD"] = (
            PERSON,
            f"ci: tweak\n\n{CO_AUTHOR}",
            ["src/app.py", ".github/workflows/ci.yml"],
        )
        validator = _validator()
        assert validator.validate(ValidationContext()) == ValidationResult.FAIL
        assert validator._checked_value == (
            ".github/workflows/ci.yml "
            "(pattern .github/workflows/*, changed by Claude Code)"
        )

    def test_a_commit_an_ai_tool_authored_may_not(self, commits):
        """No trailer to drop: the author is what the forge recorded."""
        commits["HEAD"] = (BOT, "chore: owners", ["CODEOWNERS"])
        validator = _validator()
        assert validator.validate(ValidationContext()) == ValidationResult.FAIL
        assert validator._checked_value == (
            "CODEOWNERS (pattern CODEOWNERS, changed by GitHub Copilot)"
        )

    def test_a_disclosed_tool_may_not_either(self, commits):
        commits["HEAD"] = (PERSON, "build: lock\n\nAssisted-by: Cursor", ["uv.lock"])
        validator = _validator()
        assert validator.validate(ValidationContext()) == ValidationResult.FAIL
        assert validator._checked_value == "uv.lock (pattern *.lock, changed by Cursor)"

    def test_the_projects_own_disclosure_trailer_counts(self, commits):
        commits["HEAD"] = (PERSON, "build: lock\n\nAI-assistant: Cursor", ["uv.lock"])
        assert _validator().validate(ValidationContext()) == ValidationResult.PASS
        accepting = _validator(allowed=["Assisted-by", "AI-assistant"])
        assert accepting.validate(ValidationContext()) == ValidationResult.FAIL

    def test_an_ai_commit_elsewhere_passes(self, commits):
        commits["HEAD"] = (
            PERSON,
            f"feat: app\n\n{CO_AUTHOR}",
            ["src/app.py", "docs/a.md"],
        )
        validator = _validator()
        assert validator.validate(ValidationContext()) == ValidationResult.PASS
        assert validator._checked_value == "2 path(s) changed by an AI tool"

    @pytest.mark.parametrize(
        "path", ["CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"]
    )
    def test_a_bare_pattern_matches_the_file_name_at_any_depth(self, commits, path):
        commits["HEAD"] = (BOT, "chore: owners", [path])
        assert _validator().validate(ValidationContext()) == ValidationResult.FAIL

    def test_every_offending_path_is_counted_once(self, commits, mocker):
        mocker.patch(
            "commit_check.engine.get_push_commits", return_value=["tip", "earlier"]
        )
        mocker.patch(
            "commit_check.engine.commits_new_to_remotes", side_effect=lambda revs: revs
        )
        commits["tip"] = (BOT, "ci: again", [".github/workflows/ci.yml", "uv.lock"])
        commits["earlier"] = (BOT, "ci: first", [".github/workflows/ci.yml"])
        validator = _validator()
        context = ValidationContext(stdin_text="refs/heads/f aaa refs/heads/f bbb")
        assert validator.validate(context) == ValidationResult.FAIL
        assert validator._checked_value == (
            ".github/workflows/ci.yml "
            "(pattern .github/workflows/*, changed by GitHub Copilot) (+1 more)"
        )

    def test_rev_names_the_commit(self, commits):
        commits["abc123"] = (BOT, "chore: owners", ["CODEOWNERS"])
        assert (
            _validator().validate(ValidationContext(rev="abc123"))
            == ValidationResult.FAIL
        )

    def test_a_push_answers_only_for_commits_no_remote_has(self, commits, mocker):
        """A merge of the base branch carries commits accepted there."""
        mocker.patch(
            "commit_check.engine.get_push_commits",
            return_value=["mine", "merge", "from-main"],
        )
        kept = mocker.patch(
            "commit_check.engine.commits_new_to_remotes",
            return_value=["mine", "merge"],
        )
        commits["mine"] = (PERSON, f"feat: app\n\n{CO_AUTHOR}", ["src/app.py"])
        commits["merge"] = (BOT, "Merge branch 'main' into f", [])
        commits["from-main"] = (BOT, "ci: tweak", [".github/workflows/ci.yml"])
        validator = _validator()
        context = ValidationContext(stdin_text="refs/heads/f aaa refs/heads/f bbb")
        assert validator.validate(context) == ValidationResult.PASS
        kept.assert_called_once_with(["mine", "merge", "from-main"])

    def test_a_push_with_nothing_new_is_a_skip(self, commits, mocker):
        mocker.patch("commit_check.engine.get_push_commits", return_value=["old"])
        mocker.patch("commit_check.engine.commits_new_to_remotes", return_value=[])
        context = ValidationContext(stdin_text="refs/heads/f aaa refs/heads/f bbb")
        assert _validator().validate(context) == ValidationResult.SKIP

    def test_a_deletion_only_push_is_a_skip(self, commits):
        context = ValidationContext(stdin_text=f"(delete) {ZERO} refs/heads/f abc")
        assert _validator().validate(context) == ValidationResult.SKIP

    def test_changes_that_cannot_be_read_are_a_skip_with_a_reason(self, commits):
        """The edge of a shallow clone: not validated is not the same as clean."""
        commits["HEAD"] = (BOT, "ci: tweak", None)
        validator = _validator()
        assert validator.validate(ValidationContext()) == ValidationResult.SKIP
        assert "shallow clone" in validator._skip_reason

    def test_an_offender_still_fails_beside_a_commit_that_cannot_be_read(
        self, commits, mocker
    ):
        mocker.patch(
            "commit_check.engine.get_push_commits", return_value=["tip", "edge"]
        )
        mocker.patch(
            "commit_check.engine.commits_new_to_remotes", side_effect=lambda revs: revs
        )
        commits["tip"] = (BOT, "chore: owners", ["CODEOWNERS"])
        commits["edge"] = (BOT, "ci: tweak", None)
        context = ValidationContext(stdin_text="refs/heads/f aaa refs/heads/f bbb")
        assert _validator().validate(context) == ValidationResult.FAIL

    def test_a_commit_that_cannot_be_read_is_a_skip(self, commits):
        commits["HEAD"] = (None, "", [])
        validator = _validator()
        assert validator.validate(ValidationContext()) == ValidationResult.SKIP
        assert validator._skip_reason == ""

    def test_an_ai_commit_that_changes_nothing_is_a_skip(self, commits):
        commits["HEAD"] = (BOT, "Merge branch 'main' into f", [])
        assert _validator().validate(ValidationContext()) == ValidationResult.SKIP


class TestAiFilePatternRule:
    def test_off_until_configured(self):
        rules = RuleBuilder({}).build_all_rules()
        assert "ai_file_pattern" not in {rule.check for rule in rules}

    def test_built_with_its_id_and_the_accepted_trailers(self):
        config = {
            "commit": {"ai_disclosure_trailers": ["Assisted-by", "AI-assistant"]},
            "files": {"ai_prohibited_patterns": PATTERNS},
        }
        rule = next(
            rule
            for rule in RuleBuilder(config).build_all_rules()
            if rule.check == "ai_file_pattern"
        )
        assert rule.rule_id == "CC305"
        assert rule.value == PATTERNS
        assert rule.allowed == ["Assisted-by", "AI-assistant"]
        assert "ai_prohibited_patterns" in rule.suggest

    def test_built_whatever_the_ai_attribution_policy(self):
        for policy in ("ignore", "forbid", "disclose"):
            config = {
                "commit": {"ai_attribution": policy},
                "files": {"ai_prohibited_patterns": ["CODEOWNERS"]},
            }
            checks = {rule.check for rule in RuleBuilder(config).build_all_rules()}
            assert "ai_file_pattern" in checks, policy

    def test_unusable_entries_are_dropped(self):
        config = {"files": {"ai_prohibited_patterns": ["CODEOWNERS", "", 7, "  "]}}
        rule = next(
            rule
            for rule in RuleBuilder(config).build_all_rules()
            if rule.check == "ai_file_pattern"
        )
        assert rule.value == ["CODEOWNERS"]

    def test_an_unusable_value_disables_the_rule_and_says_so(self, capsys):
        rules = RuleBuilder(
            {"files": {"ai_prohibited_patterns": "CODEOWNERS"}}
        ).build_all_rules()
        assert "ai_file_pattern" not in {rule.check for rule in rules}
        assert (
            "[files] ai_prohibited_patterns = 'CODEOWNERS' is not usable; "
            "CC305 ai-file-pattern is disabled"
        ) in capsys.readouterr().err

    def test_listed_under_warn_it_reports_without_failing(self, commits, capsys):
        commits["HEAD"] = (BOT, "chore: owners", ["CODEOWNERS"])
        config = {"warn": ["CC305"], "files": {"ai_prohibited_patterns": PATTERNS}}
        rules = [
            rule
            for rule in RuleBuilder(config).build_all_rules()
            if rule.check == "ai_file_pattern"
        ]
        outcomes = ValidationEngine(rules).validate_all_detailed(ValidationContext())
        assert [outcome.status for outcome in outcomes] == ["warn"]
        assert outcomes[0].rule_id == "CC305"


def _git(path, *args, **env):
    result = subprocess.run(
        ["git", *args],
        cwd=path,
        capture_output=True,
        check=False,
        encoding="utf-8",
        env={**os.environ, **env} if env else None,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


class TestAiFilePatternEndToEnd:
    """The rule against real commits, through the command line."""

    @pytest.fixture
    def repo(self, tmp_path, monkeypatch):
        _git(tmp_path, "init", "-q", "-b", "main")
        _git(tmp_path, "config", "user.name", PERSON[0])
        _git(tmp_path, "config", "user.email", PERSON[1])
        _git(tmp_path, "config", "commit.gpgsign", "false")
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text("on: push\n")
        (tmp_path / "CODEOWNERS").write_text("* @jane\n")
        (tmp_path / "app.py").write_text("x = 1\n")
        (tmp_path / "cchk.toml").write_text(
            '[files]\nai_prohibited_patterns = [".github/workflows/*", "CODEOWNERS"]\n'
        )
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-qm", "chore: init")
        monkeypatch.chdir(tmp_path)
        return tmp_path

    @staticmethod
    def _run(monkeypatch, *args):
        monkeypatch.setattr("sys.argv", ["commit-check", "--files", *args])
        return main()

    def test_a_person_edits_the_workflow(self, repo, monkeypatch):
        (repo / ".github" / "workflows" / "ci.yml").write_text("on: pull_request\n")
        _git(repo, "commit", "-qam", "ci: run on pull requests")
        assert self._run(monkeypatch) == 0

    def test_an_ai_commit_edits_the_application(self, repo, monkeypatch):
        (repo / "app.py").write_text("x = 2\n")
        _git(repo, "commit", "-qam", f"feat: bump x\n\n{CO_AUTHOR}")
        assert self._run(monkeypatch) == 0

    def test_an_ai_commit_edits_the_workflow(self, repo, monkeypatch, capfd):
        (repo / ".github" / "workflows" / "ci.yml").write_text("on: pull_request\n")
        _git(repo, "commit", "-qam", f"ci: run on pull requests\n\n{CO_AUTHOR}")
        assert self._run(monkeypatch) == 1
        out = capfd.readouterr().out
        assert "CC305 ai-file-pattern failed" in out
        assert ".github/workflows/ci.yml" in out
        assert "changed by Claude Code" in out

    def test_an_ai_authored_commit_deletes_codeowners(self, repo, monkeypatch, capfd):
        _git(repo, "rm", "-q", "CODEOWNERS")
        _git(
            repo,
            "commit",
            "-qm",
            "chore: drop owners",
            GIT_AUTHOR_NAME=BOT[0],
            GIT_AUTHOR_EMAIL=BOT[1],
        )
        assert self._run(monkeypatch) == 1
        assert (
            "CODEOWNERS (pattern CODEOWNERS, changed by GitHub Copilot)"
            in capfd.readouterr().out
        )

    def test_rev_judges_an_earlier_commit(self, repo, monkeypatch):
        (repo / ".github" / "workflows" / "ci.yml").write_text("on: pull_request\n")
        _git(repo, "commit", "-qam", f"ci: run on pull requests\n\n{CO_AUTHOR}")
        (repo / "app.py").write_text("x = 2\n")
        _git(repo, "commit", "-qam", "feat: bump x")
        assert self._run(monkeypatch) == 0
        assert self._run(monkeypatch, "--rev", "HEAD~1") == 1

    def test_a_pattern_given_on_the_command_line(self, repo, monkeypatch):
        (repo / "app.py").write_text("x = 2\n")
        _git(repo, "commit", "-qam", f"feat: bump x\n\n{CO_AUTHOR}")
        assert self._run(monkeypatch, "--files-ai-prohibited-patterns", "*.py") == 1
