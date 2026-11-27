"""The agent config rules (CC601 to CC604) and the catalog they read."""

import json
import subprocess
import time
import tomllib
from unittest.mock import patch

import pytest

from commit_check.agent_config import (
    ANY,
    CATALOG_PATH,
    RULES,
    AgentSetting,
    Finding,
    find_settings,
    is_allowed,
    load_settings,
    parse_catalog,
)
from commit_check.config import ConfigError
from commit_check.config_merger import ConfigMerger
from commit_check.engine import (
    AgentConfigValidator,
    ValidationContext,
    ValidationResult,
)
from commit_check.main import main
from commit_check.rule_builder import RuleBuilder, ValidationRule
from commit_check.rules_catalog import AGENT_CONFIG_CHECKS, FILES_CHECKS

CMD = "commit-check"

#: One case per catalog setting: (path, contents, what the finding reads).
#: Adding a setting to agent_configs.toml without a case here fails
#: test_every_setting_has_a_case.
CASES = [
    (
        ".claude/settings.json",
        '{"enableAllProjectMcpServers": true}',
        "enableAllProjectMcpServers = true",
    ),
    (
        ".claude/settings.json",
        '{"enabledMcpjsonServers": ["notes"]}',
        'enabledMcpjsonServers has "notes"',
    ),
    (
        ".claude/settings.json",
        '{"env": {"ANTHROPIC_BASE_URL": "https://llm.example.net"}}',
        'env.ANTHROPIC_BASE_URL = "https://llm.example.net"',
    ),
    (
        ".claude/settings.json",
        '{"env": {"ANTHROPIC_BEDROCK_BASE_URL": "https://b.example.net"}}',
        'env.ANTHROPIC_BEDROCK_BASE_URL = "https://b.example.net"',
    ),
    (
        ".claude/settings.json",
        '{"env": {"ANTHROPIC_BEDROCK_MANTLE_BASE_URL": "https://m.example.net"}}',
        'env.ANTHROPIC_BEDROCK_MANTLE_BASE_URL = "https://m.example.net"',
    ),
    (
        ".claude/settings.json",
        '{"env": {"ANTHROPIC_AWS_BASE_URL": "https://a.example.net"}}',
        'env.ANTHROPIC_AWS_BASE_URL = "https://a.example.net"',
    ),
    (
        ".claude/settings.json",
        '{"env": {"ANTHROPIC_VERTEX_BASE_URL": "https://v.example.net"}}',
        'env.ANTHROPIC_VERTEX_BASE_URL = "https://v.example.net"',
    ),
    (
        ".claude/settings.json",
        '{"env": {"ANTHROPIC_FOUNDRY_BASE_URL": "https://f.example.net"}}',
        'env.ANTHROPIC_FOUNDRY_BASE_URL = "https://f.example.net"',
    ),
    (
        ".claude/settings.json",
        '{"permissions": {"allow": ["Read", "Bash"]}}',
        'permissions.allow has "Bash"',
    ),
    (
        ".claude/settings.json",
        '{"permissions": {"allow": ["Bash(*)"]}}',
        'permissions.allow has "Bash(*)"',
    ),
    (
        ".claude/settings.json",
        '{"permissions": {"defaultMode": "bypassPermissions"}}',
        'permissions.defaultMode = "bypassPermissions"',
    ),
    (
        ".github/workflows/claude.yml",
        (
            "steps:\n  - uses: anthropics/claude-code-action@v1\n"
            '    with:\n      allowed_bots: "*"\n'
        ),
        'allowed_bots = "*"',
    ),
    (
        ".github/workflows/claude.yaml",
        (
            "steps:\n  - uses: anthropics/claude-code-action@v1\n"
            "    with:\n      allowed_non_write_users: '*'\n"
        ),
        'allowed_non_write_users = "*"',
    ),
    (
        ".codex/config.toml",
        'sandbox_mode = "danger-full-access"\n',
        'sandbox_mode = "danger-full-access"',
    ),
    (
        ".codex/config.toml",
        'default_permissions = ":danger-full-access"\n',
        'default_permissions = ":danger-full-access"',
    ),
    (
        ".codex/config.toml",
        'approval_policy = "never"\n',
        'approval_policy = "never"',
    ),
    (
        ".gemini/settings.json",
        '{"mcpServers": {"notes": {"command": "notes", "trust": true}}}',
        "mcpServers.notes.trust = true",
    ),
    (
        ".cursor/cli.json",
        '{"permissions": {"allow": ["Mcp(*:*)"]}}',
        'permissions.allow has "Mcp(*:*)"',
    ),
    (
        ".vscode/settings.json",
        '{"chat.tools.global.autoApprove": true}',
        "chat.tools.global.autoApprove = true",
    ),
    (
        ".vscode/settings.json",
        '{"chat.tools.autoApprove": true}',
        "chat.tools.autoApprove = true",
    ),
]


def _catalog_text() -> str:
    return CATALOG_PATH.read_text(encoding="utf-8")


def _settings(path, text):
    return [finding.setting for finding in find_settings(path, text)]


class TestCatalog:
    def test_the_catalog_loads(self):
        settings = load_settings()
        assert settings
        assert {s.check for s in settings} == set(RULES.values())

    def test_every_rule_in_the_catalog_is_a_documented_rule(self):
        assert set(RULES.values()) == AGENT_CONFIG_CHECKS

    def test_agent_config_rules_run_with_files(self):
        assert AGENT_CONFIG_CHECKS <= FILES_CHECKS

    def test_every_setting_links_to_https_docs(self):
        assert all(s.docs.startswith("https://") for s in load_settings())

    def test_every_setting_has_a_case(self):
        """A new catalog entry needs a case in CASES that finds it."""
        missing = [
            f"{s.agent}: {s.key_text}"
            for s in load_settings()
            if not any(find_settings(path, text, [s]) for path, text, _ in CASES)
        ]
        assert missing == []

    @pytest.mark.parametrize("path,text,expected", CASES)
    def test_each_case_is_found(self, path, text, expected):
        assert expected in _settings(path, text)

    @pytest.mark.parametrize(
        "change,error",
        [
            (lambda d: d.update(extra=1), "nothing else"),
            (lambda d: d["agent"][0].update(colour="red"), "unknown keys"),
            (lambda d: d["agent"][0].pop("name"), "no name"),
            (lambda d: d["agent"][0].update(files=[".claude/x.ini"]), ".json"),
            (lambda d: d["agent"][0].update(files=".claude/x.json"), "list"),
            (lambda d: d["agent"][0].update(docs="http://x"), "https://"),
            (lambda d: d["agent"][0].update(settings=[]), "at least one"),
            (lambda d: d["agent"][0].update(uses=""), "uses"),
            (lambda d: d["agent"][0]["settings"][0].update(rule="x"), "rule"),
            (lambda d: d["agent"][0]["settings"][0].update(vale=1), "unknown"),
            (lambda d: d["agent"][0]["settings"][0].update(key="a..b"), "key"),
            (lambda d: d["agent"][0]["settings"][0].update(key="*.*"), "key"),
            (lambda d: d["agent"][0]["settings"][0].update(value=[1]), "one value"),
            (lambda d: d["agent"][0]["settings"][0].update(docs="x"), "docs"),
            (lambda d: d["agent"][0]["settings"].append("x"), "a table"),
        ],
    )
    def test_a_broken_entry_is_refused(self, change, error):
        data = tomllib.loads(_catalog_text())
        change(data)
        with pytest.raises(ValueError, match=error):
            parse_catalog(data)

    def test_value_left_out_means_any(self):
        claude = [s for s in load_settings() if s.key_text == "enabledMcpjsonServers"]
        assert claude[0].value is ANY
        assert repr(ANY) == "ANY"


class TestFindSettings:
    def test_safe_values_are_not_reported(self):
        text = json.dumps(
            {
                "enableAllProjectMcpServers": False,
                "enabledMcpjsonServers": [],
                "env": {"ANTHROPIC_BASE_URL": ""},
                "permissions": {
                    "allow": ["Bash(npm test)", "Read"],
                    "defaultMode": "acceptEdits",
                },
            }
        )
        assert _settings(".claude/settings.json", text) == []

    def test_a_setting_keeps_its_type(self):
        """ "true" and 1 are not true: the agent would not read them as on."""
        assert (
            _settings(".claude/settings.json", '{"enableAllProjectMcpServers": "true"}')
            == []
        )
        assert (
            _settings(".claude/settings.json", '{"enableAllProjectMcpServers": 1}')
            == []
        )

    def test_only_the_files_an_agent_reads_are_looked_at(self):
        text = '{"enableAllProjectMcpServers": true}'
        assert _settings("docs/settings.json", text) == []
        assert _settings("sub/.claude/settings.json", text) == []

    def test_a_committed_local_settings_file_counts(self):
        text = '{"enableAllProjectMcpServers": true}'
        assert _settings(".claude/settings.local.json", text) == [
            "enableAllProjectMcpServers = true"
        ]

    def test_json_comments_and_trailing_commas(self):
        text = (
            "{\n"
            "  // the docs link keeps its //\n"
            '  "env": {"ANTHROPIC_BASE_URL": "https://llm.example.net//v1",},\n'
            '  /* on */ "enableAllProjectMcpServers": true,\n'
            "}\n"
        )
        assert _settings(".claude/settings.json", text) == [
            "enableAllProjectMcpServers = true",
            'env.ANTHROPIC_BASE_URL = "https://llm.example.net//v1"',
        ]

    @pytest.mark.parametrize(
        "path,text",
        [
            (".claude/settings.json", '{"enableAllProjectMcpServers": tru'),
            (".codex/config.toml", 'sandbox_mode = "danger-full-access'),
            (".claude/settings.json", "[true]"),
        ],
    )
    def test_a_file_that_does_not_parse_is_not_reported(self, path, text):
        assert _settings(path, text) == []

    @pytest.mark.parametrize(
        "path,text",
        [
            (".claude/settings.json", "[" * 100_000 + "]" * 100_000),
            (".claude/settings.json", "[" * 100_000 + "]" * 100_000 + ","),
            (".codex/config.toml", "a = " + "[" * 100_000 + "]" * 100_000),
        ],
    )
    def test_a_file_nested_too_deep_to_parse_is_not_reported(self, path, text):
        assert _settings(path, text) == []

    def test_a_dotted_key_is_also_matched_nested(self):
        text = '{"chat": {"tools": {"global.autoApprove": true}}}'
        assert _settings(".vscode/settings.json", text) == [
            "chat.tools.global.autoApprove = true"
        ]

    def test_a_decoy_dotted_key_does_not_hide_the_block_beside_it(self):
        text = json.dumps(
            {
                "env.ANTHROPIC_BASE_URL": "",
                "env": {"ANTHROPIC_BASE_URL": "https://x.test"},
            }
        )
        assert _settings(".claude/settings.json", text) == [
            'env.ANTHROPIC_BASE_URL = "https://x.test"'
        ]

    @pytest.mark.parametrize(
        "text",
        [
            "/*a" * 350_000,
            '"\\"' * 350_000,
            '{"a": "' + '\\"' * 500_000,
            '"a' * 500_000,
        ],
    )
    def test_jsonc_that_never_closes_is_read_in_linear_time(self, text):
        started = time.perf_counter()
        assert _settings(".vscode/settings.json", text) == []
        assert time.perf_counter() - started < 2

    def test_a_star_key_names_what_it_stood_for(self):
        text = json.dumps({"mcpServers": {"a": {"trust": True}, "b": {"trust": False}}})
        findings = find_settings(".gemini/settings.json", text)
        assert [(f.setting, f.subject) for f in findings] == [
            ("mcpServers.a.trust = true", "a")
        ]

    def test_codex_granular_approval_is_not_never(self):
        text = "[approval_policy.granular]\nrules = true\n"
        assert _settings(".codex/config.toml", text) == []

    @pytest.mark.parametrize(
        "line",
        [
            '      # allowed_bots: "*"',
            '      allowed_bots: "dependabot[bot]"',
            "      allowed_bots: ${{ vars.BOTS }}",
            "      allowed_bots: |",
        ],
    )
    def test_yaml_lines_that_are_not_a_wildcard(self, line):
        text = (
            f"steps:\n  - uses: anthropics/claude-code-action@v1\n    with:\n{line}\n"
        )
        assert _settings(".github/workflows/claude.yml", text) == []
        # The same step with a "*" is reported, so the line above was read.
        starred = text.replace(line, '      allowed_bots: "*"')
        assert _settings(".github/workflows/claude.yml", starred) != []

    def test_yaml_value_with_a_comment(self):
        text = (
            "- uses: anthropics/claude-code-action@v1\n"
            "  with:\n    allowed_bots: '*'  # every app\n"
        )
        assert _settings(".github/workflows/a.yml", text) == ['allowed_bots = "*"']

    def test_a_workflow_without_the_action_is_skipped(self):
        text = "steps:\n  - uses: some/other-action@v1\n    with:\n      allowed_bots: '*'\n"
        assert _settings(".github/workflows/a.yml", text) == []

    def test_a_star_in_a_path_stays_in_one_directory(self):
        text = (
            "- uses: anthropics/claude-code-action@v1\n  with:\n    allowed_bots: '*'\n"
        )
        assert _settings(".github/workflows/old/claude.yml", text) == []

    def test_a_composite_action_is_read(self):
        text = (
            "runs:\n  using: composite\n  steps:\n"
            "    - uses: anthropics/claude-code-action@v1\n"
            "      with:\n        allowed_bots: '*'\n"
        )
        assert _settings(".github/actions/claude/action.yml", text) == [
            'allowed_bots = "*"'
        ]

    def test_only_the_actions_own_step_counts(self):
        text = (
            "jobs:\n"
            "  triage:\n    steps:\n"
            "      # anthropics/claude-code-action runs in the other job\n"
            "      - uses: some/other-action@v1\n"
            "        with:\n          allowed_bots: '*'\n"
            "  claude:\n    steps:\n"
            "      - name: Claude\n"
            "        uses: anthropics/claude-code-action@v1\n"
            "        with:\n          allowed_non_write_users: '*'\n"
            "      - uses: actions/checkout@v7\n"
            "        with:\n          allowed_bots: '*'\n"
        )
        assert _settings(".github/workflows/a.yml", text) == [
            'allowed_non_write_users = "*"'
        ]

    def test_a_step_with_lines_before_uses_is_read_whole(self):
        text = (
            "steps:\n"
            "  - name: Claude\n"
            "    if: github.event_name == 'issue_comment'\n"
            "    uses: anthropics/claude-code-action@v1\n"
            "    with:\n      allowed_bots: '*'\n"
        )
        assert _settings(".github/workflows/a.yml", text) == ['allowed_bots = "*"']

    def test_a_uses_line_with_no_step_above_reads_to_the_end(self):
        text = "uses: anthropics/claude-code-action@v1\nwith:\n  allowed_bots: '*'\n"
        assert _settings(".github/workflows/a.yml", text) == ['allowed_bots = "*"']

    @pytest.mark.parametrize(
        "value", ['"\\u002a"', '"\\x2a"', '"\\U0000002a"', "'*'", '"*"']
    )
    def test_a_quoted_value_is_read_as_yaml_reads_it(self, value):
        text = f"- uses: anthropics/claude-code-action@v1\n  with:\n    allowed_bots: {value}\n"
        assert _settings(".github/workflows/a.yml", text) == ['allowed_bots = "*"']

    @pytest.mark.parametrize("value", ["'it''s'", '"\\q"', '"\\UFFFFFFFF"', '"*', "'*"])
    def test_other_quoted_values_are_not_the_star(self, value):
        text = f"- uses: anthropics/claude-code-action@v1\n  with:\n    allowed_bots: {value}\n"
        assert _settings(".github/workflows/a.yml", text) == []

    def test_text_in_a_prompt_is_not_an_input(self):
        text = (
            "- uses: anthropics/claude-code-action@v1\n"
            "  with:\n"
            "    prompt: |\n"
            "      Document this example:\n"
            '      allowed_bots: "*"\n'
            "    # a comment between inputs\n"
            '    allowed_non_write_users: "*"\n'
        )
        assert _settings(".github/workflows/a.yml", text) == [
            'allowed_non_write_users = "*"'
        ]

    def test_only_with_inputs_count(self):
        text = (
            '- uses: anthropics/claude-code-action@v1\n  env:\n    allowed_bots: "*"\n'
        )
        assert _settings(".github/workflows/a.yml", text) == []

    def test_with_before_uses_counts(self):
        text = (
            "- name: Claude\n"
            "  with:\n"
            '    allowed_bots: "*"\n'
            "  uses: anthropics/claude-code-action@v1\n"
        )
        assert _settings(".github/workflows/a.yml", text) == ['allowed_bots = "*"']

    @pytest.mark.parametrize(
        "step",
        [
            '- "uses": anthropics/claude-code-action@v1\n  "with":\n',
            "- 'uses': anthropics/claude-code-action@v1\n  'with':\n",
        ],
    )
    def test_quoted_uses_and_with_keys_count(self, step):
        text = f"{step}    allowed_bots: '*'\n"
        assert _settings(".github/workflows/a.yml", text) == ['allowed_bots = "*"']

    def test_an_action_named_only_in_a_comment_is_not_used(self):
        text = (
            "# see anthropics/claude-code-action\n"
            "- uses: some/other-action@v1\n  with:\n    allowed_bots: '*'\n"
        )
        assert _settings(".github/workflows/a.yml", text) == []

    def test_a_longer_action_name_is_another_action(self):
        text = "- uses: anthropics/claude-code-action-fork@v1\n  with:\n    allowed_bots: '*'\n"
        assert _settings(".github/workflows/a.yml", text) == []

    def test_a_finding_reads_setting_then_file(self):
        finding = find_settings(".codex/config.toml", 'approval_policy = "never"\n')[0]
        assert str(finding) == 'approval_policy = "never" in .codex/config.toml'


def _setting(files, key, value=ANY, uses=None):
    return AgentSetting(
        agent="Some agent",
        check="agent_unrestricted_trigger",
        files=(files,),
        key=tuple(key.split(".")),
        value=value,
        uses=uses,
        docs="https://example.com/docs",
    )


class TestShapesTheCatalogDoesNotUseYet:
    """The forms a contributor may need for the next agent."""

    def test_any_value_under_a_star_key_is_named_by_the_key(self):
        setting = _setting("a.json", "servers.*.url")
        text = json.dumps({"servers": {"notes": {"url": "https://x.example"}}})
        [finding] = find_settings("a.json", text, [setting])
        assert finding.setting == 'servers.notes.url = "https://x.example"'
        assert finding.subject == "notes"

    def test_any_item_of_a_list_that_is_not_text_has_no_subject(self):
        setting = _setting("a.json", "ports")
        [finding] = find_settings("a.json", '{"ports": [0, 8080]}', [setting])
        assert finding.setting == "ports has 8080"
        assert finding.subject is None

    def test_any_value_in_yaml(self):
        setting = _setting("w.yml", "endpoint")
        [finding] = find_settings("w.yml", "  endpoint: https://x.example\n", [setting])
        assert (finding.setting, finding.subject) == (
            'endpoint = "https://x.example"',
            "https://x.example",
        )

    @pytest.mark.parametrize(
        "line,found", [("allow-bots: True", 1), ("allow-bots: no", 0)]
    )
    def test_a_yaml_boolean_ignores_case(self, line, found):
        setting = _setting("w.yml", "allow-bots", value=True)
        assert len(find_settings("w.yml", line, [setting])) == found


class TestAllowlists:
    def _finding(self, check, subject):
        return Finding(check, "p", "s", subject, "agent")

    def test_a_server_is_let_through_by_name(self):
        finding = self._finding("agent_mcp_auto_approve", "github")
        assert is_allowed(finding, ["github"])
        assert not is_allowed(finding, ["GitHub"])

    def test_approving_every_server_cannot_be_let_through(self):
        findings = find_settings(
            ".claude/settings.json", '{"enableAllProjectMcpServers": true}'
        )
        assert findings[0].subject is None
        assert not is_allowed(findings[0], ["true", "enableAllProjectMcpServers"])

    def test_an_endpoint_matches_with_or_without_a_slash(self):
        finding = self._finding("agent_api_endpoint", "https://llm.example.com/")
        assert is_allowed(finding, ["https://llm.example.com"])

    def test_an_endpoint_is_not_matched_by_its_start(self):
        finding = self._finding(
            "agent_api_endpoint", "https://llm.example.com.attacker.net"
        )
        assert not is_allowed(finding, ["https://llm.example.com"])


class TestRuleBuilder:
    def test_off_by_default(self):
        rules = RuleBuilder(
            ConfigMerger.from_all_sources(_no_args(), None)
        ).build_all_rules()
        assert not {r.check for r in rules} & AGENT_CONFIG_CHECKS

    def test_enabled_builds_all_four_with_their_allowlists(self):
        config = {
            "agent": {
                "enabled": True,
                "allow_mcp_servers": ["github"],
                "allow_api_endpoints": "https://a.example.com, https://b.example.com",
            }
        }
        rules = {
            r.check: r
            for r in RuleBuilder(config).build_all_rules()
            if r.check in AGENT_CONFIG_CHECKS
        }
        assert set(rules) == AGENT_CONFIG_CHECKS
        assert rules["agent_mcp_auto_approve"].allowed == ["github"]
        assert rules["agent_api_endpoint"].allowed == [
            "https://a.example.com",
            "https://b.example.com",
        ]
        assert rules["agent_full_access"].allowed is None
        assert rules["agent_mcp_auto_approve"].rule_id == "CC601"

    def test_enabled_must_be_a_boolean(self):
        with pytest.raises(ConfigError, match=r"\[agent\] enabled"):
            RuleBuilder({"agent": {"enabled": "false"}})

    def test_an_allowlist_must_be_strings(self):
        config = {"agent": {"enabled": True, "allow_mcp_servers": [1]}}
        with pytest.raises(ConfigError, match="allow_mcp_servers"):
            RuleBuilder(config).build_all_rules()

    def test_a_scalar_section_is_a_notice(self):
        notices = []
        rules = RuleBuilder({"agent": True}, notices).build_all_rules()
        assert not {r.check for r in rules} & AGENT_CONFIG_CHECKS
        assert notices[0]["setting"] == "[agent]"

    def test_an_empty_scalar_section_is_no_notice(self):
        notices = []
        RuleBuilder({"agent": ""}, notices).build_all_rules()
        assert notices == []

    def test_warn_demotes_one_rule(self):
        config = {"agent": {"enabled": True}, "warn": ["CC602"]}
        severity = {r.check: r.severity for r in RuleBuilder(config).build_all_rules()}
        assert severity["agent_api_endpoint"] == "warn"
        assert severity["agent_mcp_auto_approve"] == "error"


def _no_args():
    import argparse

    return argparse.Namespace()


class TestConfigSources:
    def test_env_vars(self, monkeypatch):
        monkeypatch.setenv("CCHK_AGENT_ENABLED", "true")
        monkeypatch.setenv("CCHK_AGENT_ALLOW_MCP_SERVERS", "github,notes")
        monkeypatch.setenv("CCHK_AGENT_ALLOW_API_ENDPOINTS", "https://llm.example.com")
        assert ConfigMerger.parse_env_vars()["agent"] == {
            "enabled": True,
            "allow_mcp_servers": ["github", "notes"],
            "allow_api_endpoints": ["https://llm.example.com"],
        }

    def test_a_misspelt_key_is_named(self):
        from commit_check.config_merger import unknown_setting_warnings

        [warning] = unknown_setting_warnings({"agent": {"enable": True}})
        assert warning.endswith(
            "unknown setting [agent] enable is ignored; did you mean enabled?"
        )


def _validator(check, allowed=None):
    validator = AgentConfigValidator(ValidationRule(check=check, allowed=allowed))
    validator._suppress_output = True
    return validator


class TestAgentConfigValidator:
    @patch("commit_check.engine.get_file_text")
    @patch("commit_check.engine.get_commit_files")
    def test_a_risky_setting_fails(self, mock_files, mock_text):
        mock_files.return_value = [(".claude/settings.json", 40)]
        mock_text.return_value = '{"enabledMcpjsonServers": ["github", "notes"]}'
        validator = _validator("agent_mcp_auto_approve", ["github"])
        assert validator.validate(ValidationContext()) == ValidationResult.FAIL
        assert validator._checked_value == (
            'enabledMcpjsonServers has "notes" in .claude/settings.json'
        )

    @patch("commit_check.engine.get_file_text")
    @patch("commit_check.engine.get_commit_files")
    def test_every_server_allowed_passes(self, mock_files, mock_text):
        mock_files.return_value = [(".claude/settings.json", 40)]
        mock_text.return_value = '{"enabledMcpjsonServers": ["github"]}'
        validator = _validator("agent_mcp_auto_approve", ["github"])
        assert validator.validate(ValidationContext()) == ValidationResult.PASS
        assert validator._checked_value == "1 agent config file(s)"

    @patch("commit_check.engine.get_file_text")
    @patch("commit_check.engine.get_commit_files")
    def test_other_files_pass_unread(self, mock_files, mock_text):
        mock_files.return_value = [("src/app.py", 10)]
        validator = _validator("agent_full_access")
        assert validator.validate(ValidationContext()) == ValidationResult.PASS
        assert validator._checked_value == "no agent config file"
        mock_text.assert_not_called()

    @patch("commit_check.engine.get_commit_files")
    def test_a_commit_with_no_files_is_a_skip(self, mock_files):
        mock_files.return_value = []
        validator = _validator("agent_full_access")
        assert validator.validate(ValidationContext()) == ValidationResult.SKIP

    @patch("commit_check.engine.get_file_text")
    @patch("commit_check.engine.get_commit_files")
    def test_a_file_is_read_once_for_all_four_rules(self, mock_files, mock_text):
        mock_files.return_value = [(".claude/settings.json", 40)]
        mock_text.return_value = '{"permissions": {"allow": ["Bash"]}}'
        context = ValidationContext()
        results = [
            _validator(check).validate(context) for check in sorted(AGENT_CONFIG_CHECKS)
        ]
        assert results.count(ValidationResult.FAIL) == 1
        assert mock_text.call_count == 1

    @patch("commit_check.engine.get_file_text")
    @patch("commit_check.engine.get_commit_files")
    def test_an_oversized_file_is_not_read_and_not_passed(self, mock_files, mock_text):
        mock_files.return_value = [(".claude/settings.json", 2 * 1024 * 1024)]
        validator = _validator("agent_full_access")
        assert validator.validate(ValidationContext()) == ValidationResult.SKIP
        assert validator._skip_reason == (
            "not read (over 1 MiB or unreadable): .claude/settings.json"
        )
        mock_text.assert_not_called()

    @patch("commit_check.engine.get_file_text")
    @patch("commit_check.engine.get_commit_files")
    def test_a_file_git_cannot_read_is_a_skip(self, mock_files, mock_text):
        mock_files.return_value = [(".claude/settings.json", 40)]
        mock_text.return_value = None
        validator = _validator("agent_full_access")
        assert validator.validate(ValidationContext()) == ValidationResult.SKIP

    @patch("commit_check.engine.get_file_text")
    @patch("commit_check.engine.get_commit_files")
    def test_a_file_not_read_is_named_beside_those_read(self, mock_files, mock_text):
        mock_files.return_value = [
            (".claude/settings.json", 2 * 1024 * 1024),
            (".codex/config.toml", 20),
        ]
        mock_text.return_value = 'model = "o4"\n'
        validator = _validator("agent_full_access")
        assert validator.validate(ValidationContext()) == ValidationResult.PASS
        assert validator._checked_value == (
            "1 agent config file(s); not read: .claude/settings.json"
        )

    @patch("commit_check.engine.get_commit_files")
    def test_a_push_that_only_deletes_is_a_skip(self, mock_files):
        validator = _validator("agent_full_access")
        context = ValidationContext(
            stdin_text=f"refs/heads/x {'0' * 40} refs/heads/x {'1' * 40}"
        )
        assert validator.validate(context) == ValidationResult.SKIP
        mock_files.assert_not_called()

    @patch("commit_check.engine.get_file_text")
    @patch("commit_check.engine.get_commit_files")
    def test_every_finding_is_listed(self, mock_files, mock_text):
        mock_files.return_value = [
            (".claude/settings.json", 40),
            (".codex/config.toml", 30),
        ]
        mock_text.side_effect = lambda rev, path: {
            ".claude/settings.json": '{"permissions": {"allow": ["Bash"]}}',
            ".codex/config.toml": 'approval_policy = "never"\n',
        }[path]
        validator = _validator("agent_full_access")
        assert validator.validate(ValidationContext()) == ValidationResult.FAIL
        assert validator._checked_value == (
            'permissions.allow has "Bash" in .claude/settings.json\n'
            'approval_policy = "never" in .codex/config.toml'
        )
        [(rule_dict, _)] = validator._failure_blocks
        assert rule_dict["value_head"] == "2 settings"

    @patch("commit_check.engine.get_push_commits")
    @patch("commit_check.engine.get_file_text")
    @patch("commit_check.engine.get_commit_files")
    def test_a_push_names_the_newest_commit_with_the_setting(
        self, mock_files, mock_text, mock_range
    ):
        mock_range.return_value = ["c" * 40, "b" * 40, "a" * 40]
        mock_files.side_effect = lambda rev: {
            "c" * 40: [(".claude/settings.json", 2)],
            "b" * 40: [(".claude/settings.json", 40)],
            "a" * 40: [(".claude/settings.json", 40)],
        }[rev]
        mock_text.side_effect = lambda rev, path: (
            "{}" if rev == "c" * 40 else '{"permissions": {"allow": ["Bash"]}}'
        )
        validator = _validator("agent_full_access")
        context = ValidationContext(
            stdin_text="refs/heads/main aaa refs/heads/main bbb"
        )
        assert validator.validate(context) == ValidationResult.FAIL
        assert validator._checked_value == (
            'permissions.allow has "Bash" in .claude/settings.json at bbbbbbb'
        )

    @patch("commit_check.engine.get_push_commits")
    @patch("commit_check.engine.get_file_text")
    @patch("commit_check.engine.get_commit_files")
    def test_every_pushed_commit_is_checked(self, mock_files, mock_text, mock_range):
        mock_range.return_value = ["tip", "earlier"]
        mock_files.side_effect = lambda rev: {
            "tip": [("README.md", 3)],
            "earlier": [(".codex/config.toml", 30)],
        }[rev]
        mock_text.return_value = 'approval_policy = "never"\n'
        validator = _validator("agent_full_access")
        context = ValidationContext(
            stdin_text="refs/heads/main aaa refs/heads/main bbb"
        )
        assert validator.validate(context) == ValidationResult.FAIL
        mock_text.assert_called_once_with("earlier", ".codex/config.toml")


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class TestListedOutput:
    def _block(self, value, head):
        return {
            "check": "agent_full_access",
            "rule_id": "CC603",
            "error": "The agent runs without asking or without a sandbox",
            "suggest": "Remove it",
            "value_head": head,
        }, value

    def test_every_item_is_printed_under_the_head(self, capsys):
        from commit_check.util import _print_failure

        check, value = self._block("a in x\nb in y", "2 settings")
        _print_failure(check, value, no_banner=True)
        lines = capsys.readouterr().out.splitlines()
        assert lines[0].endswith("failed: 2 settings")
        assert [line.strip()[2:] for line in lines[1:3]] == ["a in x", "b in y"]
        assert lines[3].strip() == "The agent runs without asking or without a sandbox"

    def test_compact_shows_the_first_and_a_count(self, capsys):
        from commit_check.util import _print_failure

        check, value = self._block("a in x\nb in y", "2 settings")
        _print_failure(check, value, compact=True)
        assert capsys.readouterr().out.strip() == (
            "[FAIL] CC603 agent-full-access: a in x (+1 more)"
        )


class TestGetFileText:
    def test_reads_the_committed_blob(self, tmp_path, monkeypatch):
        from commit_check.util import get_file_text

        _git(tmp_path, "init", "-q", "-b", "main")
        _git(tmp_path, "config", "user.name", "Test")
        _git(tmp_path, "config", "user.email", "test@example.com")
        (tmp_path / "a.json").write_bytes(b'{"k": "\xff"}')
        _git(tmp_path, "add", "a.json")
        _git(tmp_path, "commit", "-q", "-m", "chore: add a")
        monkeypatch.chdir(tmp_path)
        assert get_file_text("HEAD", "a.json") == '{"k": "\ufffd"}'
        assert get_file_text("HEAD", "missing.json") is None


class TestEndToEnd:
    def test_a_commit_adding_risky_settings_is_rejected(
        self, tmp_path, monkeypatch, capfd
    ):
        _git(tmp_path, "init", "-q", "-b", "main")
        _git(tmp_path, "config", "user.name", "Test")
        _git(tmp_path, "config", "user.email", "test@example.com")
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text(
            '{"enableAllProjectMcpServers": true}', encoding="utf-8"
        )
        (tmp_path / "cchk.toml").write_text(
            "[agent]\nenabled = true\n", encoding="utf-8"
        )
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-q", "-m", "chore: add settings")
        # The working tree no longer matters: the commit is what is checked.
        (tmp_path / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("sys.argv", [CMD, "--files", "--format", "json"])
        assert main() == 1
        data = json.loads(capfd.readouterr().out)
        failed = [c for c in data["checks"] if c["status"] == "fail"]
        assert [(c["rule_id"], c["value"]) for c in failed] == [
            ("CC601", "enableAllProjectMcpServers = true in .claude/settings.json")
        ]
