"""CC018: a commit attributed to an AI tool links the session that produced it."""

import subprocess

import pytest

from commit_check.ai_signatures import detect_ai_signatures, detect_session_links
from commit_check.config import ConfigError
from commit_check.engine import (
    AiSessionValidator,
    ValidationContext,
    ValidationResult,
)
from commit_check.main import main
from commit_check.rule_builder import RuleBuilder, ValidationRule

PERSON = ("Jane Dev", "jane@example.com")
BOT = ("copilot-swe-agent[bot]", "198982749+Copilot@users.noreply.github.com")
CO_AUTHOR = "Co-Authored-By: Claude <noreply@anthropic.com>"

#: One line per kind of session link a known tool writes.
SESSION_LINKS = [
    ("Agent-Logs-Url: https://github.com/o/r/tasks/1", "GitHub Copilot"),
    ("Entire-Checkpoint: 01M4X1NYD0BAHNW448QYK3CBC7", "Entire"),
    ("Claude-Session: sess_abc123", "Claude Code"),
    ("https://claude.ai/code/session_016y2DnP4kiXgy", "Claude Code"),
    ("Link to Devin run: https://app.devin.ai/sessions/" + "a" * 32, "Devin"),
    ("Codex Cloud task: https://chatgpt.com/codex/tasks/task_e_abc", "OpenAI Codex"),
]


def _validator(own=None, allowed=None):
    rule = ValidationRule(check="ai_session", value=own or [], allowed=allowed)
    validator = AiSessionValidator(rule)
    validator._suppress_output = True
    return validator


@pytest.fixture
def author(mocker):
    """The identity git would record for a piped message; a person by default."""
    patched = mocker.patch(
        "commit_check.engine.get_pending_author_identity", return_value=PERSON
    )
    mocker.patch("commit_check.engine.has_commits", return_value=True)
    return patched


def _judge(message, own=None, allowed=None):
    validator = _validator(own, allowed)
    result = validator.validate(ValidationContext(stdin_text=message))
    return result, validator


class TestSessionLinks:
    @pytest.mark.parametrize(("line", "tool"), SESSION_LINKS)
    def test_each_known_link_is_a_session_link(self, line, tool):
        links = detect_session_links(f"fix: typo\n\n{line}")
        assert [s["tool"] for s in links] == [tool]

    def test_other_marks_are_not_session_links(self):
        message = (
            "fix: typo\n\n"
            "🤖 Generated with [Claude Code](https://claude.com/claude-code)\n"
            f"{CO_AUTHOR}\n"
            "Assisted-by: Cursor\n"
            "Claude-Workflow: wf_1"
        )
        assert detect_ai_signatures(message)
        assert detect_session_links(message) == []

    def test_a_session_url_cited_in_a_sentence_is_not_a_link(self):
        message = "docs: explain\n\nSee https://claude.ai/code/session_016y for why."
        assert detect_session_links(message) == []

    def test_an_entire_checkpoint_is_a_stamp(self):
        """Entire records the agent's session, so its trailer marks AI use."""
        (signature,) = detect_ai_signatures(
            "fix: typo\n\nEntire-Checkpoint: 01M4X1NYD0BAHNW448QYK3CBC7"
        )
        assert signature["tool"] == "Entire"
        assert signature["role"] == "stamp"
        assert signature["trailer"] == "Entire-Checkpoint"

    def test_entire_is_not_read_into_the_word(self):
        """A disclosure of "the entire team" names no tool called Entire."""
        (signature,) = detect_ai_signatures("fix: typo\n\nAssisted-by: the entire team")
        assert signature["tool"] == "Generic AI"


@pytest.mark.usefixtures("author")
class TestAiSessionValidator:
    def test_a_person_commit_passes(self):
        result, validator = _judge("fix: typo")
        assert result == ValidationResult.PASS
        assert validator._checked_value == "no commit attributed to an AI tool"

    @pytest.mark.parametrize(
        "line",
        [CO_AUTHOR, "Assisted-by: Claude Code", "Assisted-by: SomeNewAgent 1.2"],
    )
    def test_an_ai_commit_without_a_link_fails(self, line):
        result, validator = _judge(f"fix: typo\n\n{line}")
        assert result == ValidationResult.FAIL
        assert validator._checked_value.endswith(", no session link")

    def test_the_failure_names_the_tool(self):
        result, validator = _judge(f"fix: typo\n\n{CO_AUTHOR}")
        assert result == ValidationResult.FAIL
        ((failure, value),) = validator._failure_blocks
        assert value == "Claude Code, no session link"
        assert failure["error"] == (
            "A commit attributed to Claude Code does not link the session that "
            "produced it"
        )

    @pytest.mark.parametrize(("line", "_tool"), SESSION_LINKS)
    def test_a_known_link_passes(self, line, _tool):
        result, validator = _judge(f"fix: typo\n\nAssisted-by: Claude Code\n{line}")
        assert result == ValidationResult.PASS
        # A body marker reports the link itself, not the words around it.
        assert validator._checked_value in line

    def test_a_link_alone_attributes_and_satisfies(self):
        """A session link is a stamp: it names the tool and links its session."""
        result, _ = _judge("fix: typo\n\nAgent-Logs-Url: https://github.com/o/r/1")
        assert result == ValidationResult.PASS

    def test_the_projects_own_trailer_counts(self):
        message = "fix: typo\n\nAssisted-by: Claude Code\nagent-session: https://x/1"
        result, validator = _judge(message, own=["Agent-Session"])
        assert result == ValidationResult.PASS
        assert validator._checked_value == "agent-session: https://x/1"

    def test_the_projects_own_trailer_needs_a_value(self):
        message = "fix: typo\n\nAssisted-by: Claude Code\nAgent-Session:"
        result, _ = _judge(message, own=["Agent-Session"])
        assert result == ValidationResult.FAIL

    def test_an_unlisted_trailer_does_not_count(self):
        message = "fix: typo\n\nAssisted-by: Claude Code\nAgent-Session: https://x/1"
        result, _ = _judge(message)
        assert result == ValidationResult.FAIL

    def test_a_disclosure_counts_under_the_trailers_the_project_accepts(self):
        message = "fix: typo\n\nAI-assistant: SomeNewAgent 1.2"
        assert _judge(message)[0] == ValidationResult.PASS
        result, _ = _judge(message, allowed=["Assisted-by", "AI-assistant"])
        assert result == ValidationResult.FAIL

    def test_an_ai_author_needs_a_link(self, author):
        author.return_value = BOT
        assert _judge("fix: typo")[0] == ValidationResult.FAIL
        message = "fix: typo\n\nAgent-Logs-Url: https://github.com/o/r/1"
        assert _judge(message)[0] == ValidationResult.PASS

    def test_an_ignored_co_author_skips(self, mocker):
        mocker.patch("commit_check.engine.get_git_config_value", return_value="Jane")
        validator = _validator()
        context = ValidationContext(
            stdin_text="fix: typo\n\nCo-authored-by: Claude <noreply@anthropic.com>",
            config={"commit": {"ignore_authors": ["Claude"]}},
        )
        assert validator.validate(context) == ValidationResult.SKIP


class TestNoCommitsYet:
    def test_a_repository_without_commits_skips(self, mocker):
        mocker.patch("commit_check.engine.has_commits", return_value=False)
        validator = _validator()
        assert validator.validate(ValidationContext()) == ValidationResult.SKIP


def _session_rule(commit_config):
    rules = RuleBuilder({"commit": commit_config}).build_all_rules()
    return next((r for r in rules if r.check == "ai_session"), None)


class TestAiSessionRuleBuilder:
    def test_off_by_default(self):
        assert _session_rule({}) is None
        assert _session_rule({"ai_attribution": "disclose"}) is None

    @pytest.mark.parametrize("policy", ["ignore", "disclose"])
    def test_built_when_required(self, policy):
        rule = _session_rule({"require_ai_session": True, "ai_attribution": policy})
        assert rule is not None
        assert rule.rule_id == "CC018"
        assert rule.value == []
        assert rule.allowed == ["Assisted-by", "Generated-by"]
        assert rule.suggest == (
            "Add the link the tool records for its session, such as an "
            "Agent-Logs-Url: or Entire-Checkpoint: trailer"
        )

    def test_not_built_under_forbid(self):
        """An AI commit fails CC013 there, link or not."""
        config = {"require_ai_session": True, "ai_attribution": "forbid"}
        assert _session_rule(config) is None

    def test_it_reads_the_accepted_disclosure_trailers(self):
        config = {"require_ai_session": True, "ai_disclosure_trailers": ["AI-tool"]}
        assert _session_rule(config).allowed == ["AI-tool"]

    def test_the_suggestion_names_the_projects_own_trailer(self):
        config = {
            "require_ai_session": True,
            "ai_session_trailers": ["Agent-Session:", "agent-session", " Run-Url "],
        }
        rule = _session_rule(config)
        assert rule.value == ["Agent-Session", "Run-Url"]
        assert rule.suggest.endswith("; this project also accepts Agent-Session:")

    @pytest.mark.parametrize(
        ("trailers", "expected"),
        [
            ("Agent-Session, Run-Url", ["Agent-Session", "Run-Url"]),
            ("Agent-Session", ["Agent-Session"]),
            (["Agent-Session", ""], ["Agent-Session"]),
            ("", []),
        ],
    )
    def test_trailers_from_strings_and_lists(self, trailers, expected):
        config = {"require_ai_session": True, "ai_session_trailers": trailers}
        assert _session_rule(config).value == expected

    @pytest.mark.parametrize("trailers", [["not a token"], [True], 7, ["Run:Url"]])
    def test_unusable_trailers_are_config_errors(self, trailers):
        config = {"require_ai_session": True, "ai_session_trailers": trailers}
        with pytest.raises(ConfigError) as excinfo:
            _session_rule(config)
        assert excinfo.value.setting == "[commit] ai_session_trailers"

    @pytest.mark.parametrize("value", ["yes", 1, None])
    def test_require_must_be_a_boolean(self, value):
        with pytest.raises(ConfigError) as excinfo:
            _session_rule({"require_ai_session": value})
        assert excinfo.value.setting == "[commit] require_ai_session"
        assert "must be true or false" in str(excinfo.value)

    def test_warn_accepts_the_rule(self):
        rules = RuleBuilder(
            {"warn": ["CC018"], "commit": {"require_ai_session": True}}
        ).build_all_rules()
        (rule,) = [r for r in rules if r.check == "ai_session"]
        assert rule.severity == "warn"


class TestSettings:
    def test_env_vars_reach_config(self, monkeypatch):
        from commit_check.config_merger import ConfigMerger

        monkeypatch.setenv("CCHK_REQUIRE_AI_SESSION", "true")
        monkeypatch.setenv("CCHK_AI_SESSION_TRAILERS", "Agent-Session,Run-Url")
        config = ConfigMerger.parse_env_vars()
        assert config["commit"] == {
            "require_ai_session": True,
            "ai_session_trailers": ["Agent-Session", "Run-Url"],
        }

    def test_cli_options_reach_config(self):
        from commit_check.config_merger import ConfigMerger
        from commit_check.main import _get_parser

        args = _get_parser().parse_args(
            ["-m", "--require-ai-session", "yes", "--ai-session-trailers", "A-B,C"]
        )
        config = ConfigMerger.parse_cli_args(args)
        assert config["commit"] == {
            "require_ai_session": True,
            "ai_session_trailers": ["A-B", "C"],
        }


class TestEndToEnd:
    @pytest.fixture
    def repo(self, tmp_path, monkeypatch, mocker):
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        monkeypatch.chdir(tmp_path)
        mocker.patch(
            "commit_check.engine.get_git_config_value", return_value="test-author"
        )
        mocker.patch(
            "commit_check.engine.get_pending_author_identity", return_value=PERSON
        )
        (tmp_path / "cchk.toml").write_text(
            '[commit]\nrequire_ai_session = true\nai_attribution = "disclose"\n'
        )
        return tmp_path

    def _run(self, mocker, monkeypatch, message):
        mocker.patch("sys.stdin.isatty", return_value=False)
        mocker.patch("sys.stdin.read", return_value=message)
        mocker.patch(
            "commit_check.main.StdinReader._has_pending_data", return_value=True
        )
        monkeypatch.setattr("sys.argv", ["commit-check", "--message"])
        return main()

    def test_a_disclosed_commit_without_a_link_is_rejected(
        self, repo, mocker, monkeypatch, capfd
    ):
        message = "fix: typo\n\nAssisted-by: Claude Code\n"
        assert self._run(mocker, monkeypatch, message) == 1
        out, err = capfd.readouterr()
        assert "CC018" in out + err
        assert "does not link the session that produced it" in out + err

    def test_a_linked_commit_passes(self, repo, mocker, monkeypatch):
        message = (
            "fix: typo\n\nAssisted-by: Claude Code\n"
            "Entire-Checkpoint: 01M4X1NYD0BAHNW448QYK3CBC7\n"
        )
        assert self._run(mocker, monkeypatch, message) == 0
