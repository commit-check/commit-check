"""Tests for config_merger module."""

import os
import pytest
import argparse
from commit_check.config_merger import (
    parse_bool,
    parse_list,
    parse_int,
    get_default_config,
    deep_merge,
    ConfigMerger,
)


class TestParseBool:
    """Tests for parse_bool function."""

    def test_parse_bool_from_bool(self):
        assert parse_bool(True) is True
        assert parse_bool(False) is False

    def test_parse_bool_from_int(self):
        assert parse_bool(1) is True
        assert parse_bool(0) is False

    def test_parse_bool_from_string_true_variants(self):
        for value in ["true", "True", "TRUE", "yes", "YES", "y", "Y", "t", "T", "1"]:
            assert parse_bool(value) is True, f"Failed for '{value}'"

    def test_parse_bool_from_string_false_variants(self):
        for value in ["false", "False", "FALSE", "no", "NO", "n", "N", "f", "F", "0"]:
            assert parse_bool(value) is False, f"Failed for '{value}'"

    def test_parse_bool_invalid_string(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_bool("invalid")

    def test_parse_bool_invalid_type(self):
        with pytest.raises(TypeError, match="Cannot convert"):
            parse_bool([])


class TestParseList:
    """Tests for parse_list function."""

    def test_parse_list_from_list(self):
        assert parse_list(["a", "b", "c"]) == ["a", "b", "c"]

    def test_parse_list_from_comma_separated(self):
        assert parse_list("a,b,c") == ["a", "b", "c"]

    def test_parse_list_from_comma_separated_with_spaces(self):
        assert parse_list("a, b , c") == ["a", "b", "c"]

    def test_parse_list_empty_string(self):
        assert parse_list("") == []

    def test_parse_list_single_item(self):
        assert parse_list("single") == ["single"]

    def test_parse_list_invalid_type(self):
        with pytest.raises(TypeError, match="Cannot convert"):
            parse_list(123)


class TestParseInt:
    """Tests for parse_int function."""

    def test_parse_int_from_int(self):
        assert parse_int(42) == 42

    def test_parse_int_from_string(self):
        assert parse_int("42") == 42
        assert parse_int(" 42 ") == 42

    def test_parse_int_invalid_string(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_int("invalid")

    def test_parse_int_invalid_type(self):
        with pytest.raises(TypeError, match="Cannot convert"):
            parse_int([])


class TestGetDefaultConfig:
    """Tests for get_default_config function."""

    def test_returns_dict(self):
        config = get_default_config()
        assert isinstance(config, dict)

    def test_has_commit_section(self):
        config = get_default_config()
        assert "commit" in config
        assert isinstance(config["commit"], dict)

    def test_has_branch_section(self):
        config = get_default_config()
        assert "branch" in config
        assert isinstance(config["branch"], dict)

    def test_commit_defaults(self):
        config = get_default_config()
        commit = config["commit"]
        assert commit["conventional_commits"] is True
        assert commit["subject_max_length"] == 80
        assert commit["subject_min_length"] == 5
        assert isinstance(commit["allow_commit_types"], list)
        assert "feat" in commit["allow_commit_types"]

    def test_branch_defaults(self):
        config = get_default_config()
        branch = config["branch"]
        assert branch["conventional_branch"] is True
        assert isinstance(branch["allow_branch_types"], list)
        assert "feature" in branch["allow_branch_types"]


class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_merge_simple_keys(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        deep_merge(base, override)
        assert base == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested_dicts(self):
        base = {"section": {"key1": "value1", "key2": "value2"}}
        override = {"section": {"key2": "new_value2", "key3": "value3"}}
        deep_merge(base, override)
        assert base == {
            "section": {"key1": "value1", "key2": "new_value2", "key3": "value3"}
        }

    def test_override_with_non_dict(self):
        base = {"section": {"key": "value"}}
        override = {"section": "not_a_dict"}
        deep_merge(base, override)
        assert base == {"section": "not_a_dict"}


class TestConfigMergerParseEnvVars:
    """Tests for ConfigMerger.parse_env_vars method."""

    def test_parse_boolean_env_var(self, monkeypatch):
        monkeypatch.setenv("CCHK_SUBJECT_IMPERATIVE", "true")
        config = ConfigMerger.parse_env_vars()
        assert config["commit"]["subject_imperative"] is True

    def test_parse_integer_env_var(self, monkeypatch):
        monkeypatch.setenv("CCHK_SUBJECT_MAX_LENGTH", "100")
        config = ConfigMerger.parse_env_vars()
        assert config["commit"]["subject_max_length"] == 100

    def test_parse_list_env_var(self, monkeypatch):
        monkeypatch.setenv("CCHK_ALLOW_COMMIT_TYPES", "feat,fix,docs")
        config = ConfigMerger.parse_env_vars()
        assert config["commit"]["allow_commit_types"] == ["feat", "fix", "docs"]

    def test_parse_multiple_env_vars(self, monkeypatch):
        monkeypatch.setenv("CCHK_SUBJECT_IMPERATIVE", "false")
        monkeypatch.setenv("CCHK_SUBJECT_MAX_LENGTH", "72")
        monkeypatch.setenv("CCHK_ALLOW_MERGE_COMMITS", "false")
        config = ConfigMerger.parse_env_vars()
        assert config["commit"]["subject_imperative"] is False
        assert config["commit"]["subject_max_length"] == 72
        assert config["commit"]["allow_merge_commits"] is False

    def test_parse_branch_env_vars(self, monkeypatch):
        monkeypatch.setenv("CCHK_CONVENTIONAL_BRANCH", "false")
        monkeypatch.setenv("CCHK_ALLOW_BRANCH_TYPES", "feature,bugfix")
        config = ConfigMerger.parse_env_vars()
        assert config["branch"]["conventional_branch"] is False
        assert config["branch"]["allow_branch_types"] == ["feature", "bugfix"]

    def test_invalid_env_var_is_skipped(self, monkeypatch, capsys):
        monkeypatch.setenv("CCHK_SUBJECT_MAX_LENGTH", "invalid")
        config = ConfigMerger.parse_env_vars()
        # Should not crash, but should print warning
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        # Should not have subject_max_length in config
        assert "subject_max_length" not in config.get("commit", {})

    def test_no_env_vars_returns_empty_sections(self, monkeypatch):
        # Clear all CCHK_ environment variables
        for key in list(os.environ.keys()):
            if key.startswith("CCHK_"):
                monkeypatch.delenv(key, raising=False)

        config = ConfigMerger.parse_env_vars()
        # Should return empty dict or dict with empty sections
        assert not config or all(not v for v in config.values())


class TestConfigMergerParseCliArgs:
    """Tests for ConfigMerger.parse_cli_args method."""

    def test_parse_boolean_cli_arg(self):
        args = argparse.Namespace(subject_imperative=True)
        config = ConfigMerger.parse_cli_args(args)
        assert config["commit"]["subject_imperative"] is True

    def test_parse_integer_cli_arg(self):
        args = argparse.Namespace(subject_max_length=100)
        config = ConfigMerger.parse_cli_args(args)
        assert config["commit"]["subject_max_length"] == 100

    def test_parse_list_cli_arg(self):
        args = argparse.Namespace(allow_commit_types=["feat", "fix", "docs"])
        config = ConfigMerger.parse_cli_args(args)
        assert config["commit"]["allow_commit_types"] == ["feat", "fix", "docs"]

    def test_parse_multiple_cli_args(self):
        args = argparse.Namespace(
            subject_imperative=False,
            subject_max_length=72,
            allow_merge_commits=False,
        )
        config = ConfigMerger.parse_cli_args(args)
        assert config["commit"]["subject_imperative"] is False
        assert config["commit"]["subject_max_length"] == 72
        assert config["commit"]["allow_merge_commits"] is False

    def test_none_values_are_not_included(self):
        args = argparse.Namespace(subject_imperative=None, subject_max_length=100)
        config = ConfigMerger.parse_cli_args(args)
        assert "subject_imperative" not in config.get("commit", {})
        assert config["commit"]["subject_max_length"] == 100

    def test_missing_attributes_are_ignored(self):
        args = argparse.Namespace()
        config = ConfigMerger.parse_cli_args(args)
        # Should not crash, should return empty sections
        assert not config or all(not v for v in config.values())

    def test_branch_cli_args(self):
        args = argparse.Namespace(
            conventional_branch=False,
            allow_branch_types=["feature", "bugfix"],
            require_rebase_target="main",
        )
        config = ConfigMerger.parse_cli_args(args)
        assert config["branch"]["conventional_branch"] is False
        assert config["branch"]["allow_branch_types"] == ["feature", "bugfix"]
        assert config["branch"]["require_rebase_target"] == "main"


class TestConfigMergerFromAllSources:
    """Tests for ConfigMerger.from_all_sources method."""

    def test_default_config_only(self, tmp_path):
        # No TOML file, no env vars, no CLI args
        args = argparse.Namespace()
        config = ConfigMerger.from_all_sources(args)

        # Should have default values
        assert config["commit"]["conventional_commits"] is True
        assert config["commit"]["subject_max_length"] == 80

    def test_toml_overrides_defaults(self, tmp_path, monkeypatch):
        # Create a TOML config file
        toml_file = tmp_path / "cchk.toml"
        toml_file.write_text("""
[commit]
subject_max_length = 100
subject_imperative = true
""")

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        args = argparse.Namespace()
        config = ConfigMerger.from_all_sources(args)

        assert config["commit"]["subject_max_length"] == 100
        assert config["commit"]["subject_imperative"] is True
        # Defaults should still be present for other keys
        assert config["commit"]["conventional_commits"] is True

    def test_env_overrides_toml(self, tmp_path, monkeypatch):
        # Create a TOML config file
        toml_file = tmp_path / "cchk.toml"
        toml_file.write_text("""
[commit]
subject_max_length = 100
""")

        # Set env var
        monkeypatch.setenv("CCHK_SUBJECT_MAX_LENGTH", "120")
        monkeypatch.chdir(tmp_path)

        args = argparse.Namespace()
        config = ConfigMerger.from_all_sources(args)

        # Env var should override TOML
        assert config["commit"]["subject_max_length"] == 120

    def test_cli_overrides_env(self, tmp_path, monkeypatch):
        # Create a TOML config file
        toml_file = tmp_path / "cchk.toml"
        toml_file.write_text("""
[commit]
subject_max_length = 100
""")

        # Set env var
        monkeypatch.setenv("CCHK_SUBJECT_MAX_LENGTH", "120")
        monkeypatch.chdir(tmp_path)

        # Set CLI arg
        args = argparse.Namespace(subject_max_length=150)
        config = ConfigMerger.from_all_sources(args)

        # CLI should override both env and TOML
        assert config["commit"]["subject_max_length"] == 150

    def test_priority_chain_full(self, tmp_path, monkeypatch):
        """Test full priority chain: CLI > Env > TOML > Defaults"""
        # Create TOML config
        toml_file = tmp_path / "cchk.toml"
        toml_file.write_text("""
[commit]
subject_max_length = 100
subject_min_length = 10
subject_imperative = true
allow_merge_commits = false
""")

        # Set env vars (override some TOML values)
        monkeypatch.setenv("CCHK_SUBJECT_MAX_LENGTH", "120")
        monkeypatch.setenv("CCHK_SUBJECT_IMPERATIVE", "false")
        monkeypatch.chdir(tmp_path)

        # Set CLI args (override some env values)
        args = argparse.Namespace(
            subject_max_length=150,
            allow_merge_commits=True,
        )
        config = ConfigMerger.from_all_sources(args)

        # Verify priorities:
        assert config["commit"]["subject_max_length"] == 150  # CLI wins
        assert config["commit"]["subject_imperative"] is False  # Env wins (no CLI)
        assert config["commit"]["subject_min_length"] == 10  # TOML wins (no CLI or env)
        assert config["commit"]["allow_merge_commits"] is True  # CLI wins
        assert config["commit"]["conventional_commits"] is True  # Default wins

    def test_specific_config_path(self, tmp_path):
        # Create a custom config file
        custom_config = tmp_path / "custom.toml"
        custom_config.write_text("""
[commit]
subject_max_length = 200
""")

        args = argparse.Namespace()
        config = ConfigMerger.from_all_sources(args, str(custom_config))

        assert config["commit"]["subject_max_length"] == 200

    def test_missing_specific_config_raises_error(self, tmp_path):
        args = argparse.Namespace()
        with pytest.raises(FileNotFoundError):
            ConfigMerger.from_all_sources(args, str(tmp_path / "nonexistent.toml"))
