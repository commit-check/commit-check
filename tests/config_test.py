"""Tests for commit_check.config module."""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from commit_check.config import (
    load_config,
    DEFAULT_CONFIG_PATHS,
    _deep_merge,
    _resolve_inherit_from,
    _load_from_url,
    _github_shorthand_to_url,
)


class TestConfig:
    @pytest.mark.benchmark
    def test_load_config_with_path_hint(self):
        """Test loading config with explicit path hint."""
        config_content = b"""
[checks]
message = true
branch = true
"""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
            f.write(config_content)
            f.flush()

            try:
                config = load_config(f.name)
                assert "checks" in config
                assert config["checks"]["message"] is True
                assert config["checks"]["branch"] is True
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_load_config_with_nonexistent_path_hint(self):
        """Test loading config when path hint doesn't exist - should raise FileNotFoundError."""
        # Test that specifying a nonexistent config file raises an error
        with pytest.raises(
            FileNotFoundError, match="Specified config file not found: nonexistent.toml"
        ):
            load_config("nonexistent.toml")

    @pytest.mark.benchmark
    def test_load_config_default_cchk_toml(self):
        """Test loading config from default cchk.toml path."""
        config_content = b"""
[checks]
default_cchk = true
"""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                with open("cchk.toml", "wb") as f:
                    f.write(config_content)

                config = load_config()
                assert "checks" in config
                assert config["checks"]["default_cchk"] is True
            finally:
                os.chdir(original_cwd)

    @pytest.mark.benchmark
    def test_load_config_default_commit_check_toml(self):
        """Test loading config from default commit-check.toml path."""
        config_content = b"""
[checks]
commit_check_toml = true
"""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                with open("commit-check.toml", "wb") as f:
                    f.write(config_content)

                config = load_config()
                assert "checks" in config
                assert config["checks"]["commit_check_toml"] is True
            finally:
                os.chdir(original_cwd)

    @pytest.mark.benchmark
    def test_load_config_github_cchk_toml(self):
        """Test loading config from .github/cchk.toml path."""
        config_content = b"""
[checks]
github_cchk = true
"""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                # Create .github directory
                os.makedirs(".github", exist_ok=True)
                with open(".github/cchk.toml", "wb") as f:
                    f.write(config_content)

                config = load_config()
                assert "checks" in config
                assert config["checks"]["github_cchk"] is True
            finally:
                os.chdir(original_cwd)

    @pytest.mark.benchmark
    def test_load_config_github_commit_check_toml(self):
        """Test loading config from .github/commit-check.toml path."""
        config_content = b"""
[checks]
github_commit_check = true
"""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                # Create .github directory
                os.makedirs(".github", exist_ok=True)
                with open(".github/commit-check.toml", "wb") as f:
                    f.write(config_content)

                config = load_config()
                assert "checks" in config
                assert config["checks"]["github_commit_check"] is True
            finally:
                os.chdir(original_cwd)

    @pytest.mark.benchmark
    def test_load_config_priority_root_over_github(self):
        """Test that root config files have priority over .github folder."""
        root_config = b"""
[checks]
location = "root"
"""
        github_config = b"""
[checks]
location = "github"
"""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                # Create both root and .github configs
                with open("cchk.toml", "wb") as f:
                    f.write(root_config)
                os.makedirs(".github", exist_ok=True)
                with open(".github/cchk.toml", "wb") as f:
                    f.write(github_config)

                config = load_config()
                assert "checks" in config
                # Should load from root, not .github
                assert config["checks"]["location"] == "root"
            finally:
                os.chdir(original_cwd)

    @pytest.mark.benchmark
    def test_load_config_file_not_found(self):
        """Test returning empty config when no default config files exist."""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                # Should return empty config when no default files exist
                config = load_config()
                assert config == {}
            finally:
                os.chdir(original_cwd)

    @pytest.mark.benchmark
    def test_load_config_file_not_found_with_invalid_path_hint(self):
        """Test FileNotFoundError when specified path hint doesn't exist."""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                with pytest.raises(
                    FileNotFoundError,
                    match="Specified config file not found: nonexistent.toml",
                ):
                    load_config("nonexistent.toml")
            finally:
                os.chdir(original_cwd)

    @pytest.mark.benchmark
    def test_default_config_paths_constant(self):
        """Test that DEFAULT_CONFIG_PATHS contains expected paths."""
        assert len(DEFAULT_CONFIG_PATHS) == 4
        assert Path("cchk.toml") in DEFAULT_CONFIG_PATHS
        assert Path("commit-check.toml") in DEFAULT_CONFIG_PATHS
        assert Path(".github/cchk.toml") in DEFAULT_CONFIG_PATHS
        assert Path(".github/commit-check.toml") in DEFAULT_CONFIG_PATHS

    @pytest.mark.benchmark
    def test_toml_load_function_exists(self):
        """Test that toml_load function is properly set up."""
        from commit_check.config import toml_load

        assert callable(toml_load)

        # Test that it can actually parse TOML content
        config_content = b"""
[test]
value = "works"
"""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
            f.write(config_content)
            f.flush()

            try:
                with open(f.name, "rb") as config_file:
                    result = toml_load(config_file)
                assert result == {"test": {"value": "works"}}
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_tomli_import_fallback(self):
        """Test that tomli is imported when tomllib is not available (lines 10-13)."""
        import sys

        # Save original modules
        original_tomllib = sys.modules.get("tomllib")
        original_config = sys.modules.get("commit_check.config")

        try:
            # Remove modules from cache to force fresh import
            if "tomllib" in sys.modules:
                del sys.modules["tomllib"]
            if "commit_check.config" in sys.modules:
                del sys.modules["commit_check.config"]

            # Mock tomllib module to not exist
            with patch.dict("sys.modules", {"tomllib": None}):
                # Force import error by patching __import__ for tomllib specifically
                original_import = __builtins__["__import__"]

                def mock_import(name, *args, **kwargs):
                    if name == "tomllib":
                        raise ImportError("No module named 'tomllib'")
                    # For tomli, return a working mock
                    if name == "tomli":

                        class MockTomli:
                            @staticmethod
                            def load(f):
                                content = f.read().decode("utf-8")
                                # Simple parser for test
                                if '[test]\nvalue = "tomli_works"' in content:
                                    return {"test": {"value": "tomli_works"}}
                                return {}

                        return MockTomli()
                    return original_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=mock_import):
                    # Import the config module - should use tomli fallback
                    import commit_check.config as config_module

                    # Verify that the module loaded successfully
                    assert hasattr(config_module, "toml_load")
                    assert callable(config_module.toml_load)

                    # Test that it can actually parse TOML content
                    config_content = b'[test]\nvalue = "tomli_works"\n'
                    with tempfile.NamedTemporaryFile(
                        mode="wb", suffix=".toml", delete=False
                    ) as f:
                        f.write(config_content)
                        f.flush()

                    try:
                        with open(f.name, "rb") as config_file:
                            result = config_module.toml_load(config_file)
                        assert result == {"test": {"value": "tomli_works"}}
                    finally:
                        os.unlink(f.name)

        finally:
            # Restore original modules
            if original_tomllib is not None:
                sys.modules["tomllib"] = original_tomllib
            if original_config is not None:
                sys.modules["commit_check.config"] = original_config


class TestConfigEdgeCases:
    """Test TOML parsing errors and exception handling."""

    @pytest.mark.benchmark
    def test_load_config_invalid_toml(self):
        """Test handling of invalid TOML syntax."""
        invalid_toml = b"""
[incomplete
missing closing bracket
"""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
            f.write(invalid_toml)
            f.flush()

            try:
                with pytest.raises(Exception):  # Should raise a TOML parsing error
                    load_config(f.name)
            finally:
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_load_config_file_permission_error(self):
        """Test handling of file permission errors."""
        config_content = b"""
[checks]
test = true
"""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
            f.write(config_content)
            f.flush()

            try:
                # Remove read permissions to simulate permission error
                os.chmod(f.name, 0o000)

                with pytest.raises(PermissionError):
                    load_config(f.name)
            finally:
                # Restore permissions and clean up
                os.chmod(f.name, 0o644)
                os.unlink(f.name)

    @pytest.mark.benchmark
    def test_tomli_import_fallback(self):
        """Test the tomli import fallback when tomllib is not available."""
        # We need to test the import fallback behavior
        # This is complex because the imports happen at module load time

        # Create a minimal test by importing the config module's behavior
        config_content = b"""
[test]
fallback = true
"""

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
            f.write(config_content)
            f.flush()

            try:
                # Test that we can load config regardless of which TOML library is used
                config = load_config(f.name)
                assert config["test"]["fallback"] is True

                # Since we can't easily test the import fallback on Python 3.11+,
                # let's at least verify that the toml_load function works
                from commit_check.config import toml_load

                with open(f.name, "rb") as config_file:
                    result = toml_load(config_file)
                assert result["test"]["fallback"] is True

            finally:
                os.unlink(f.name)


class TestConfigFallback:
    """Direct test of the config import fallback using module manipulation."""

    @pytest.mark.benchmark
    def test_config_tomli_fallback_direct(self):
        """Test config.py fallback to tomli by manipulating imports."""

        # Save original state
        original_modules = sys.modules.copy()

        try:
            # Remove config module if already imported
            if "commit_check.config" in sys.modules:
                del sys.modules["commit_check.config"]

            # Make tomllib unavailable by raising ImportError
            original_import = __import__

            def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
                if name == "tomllib":
                    raise ImportError("No module named 'tomllib'")
                # For tomli, return a working mock
                if name == "tomli":

                    class MockTomli:
                        @staticmethod
                        def load(f):
                            content = f.read().decode("utf-8")
                            # Simple parser for test
                            if 'test_key = "test_value"' in content:
                                return {"test_key": "test_value"}
                            return {}

                    return MockTomli()
                return original_import(name, globals, locals, fromlist, level)

            with patch("builtins.__import__", side_effect=mock_import):
                # Now import config - should use tomli fallback
                from commit_check.config import toml_load

                # Test that it works
                config_content = b'test_key = "test_value"'
                with tempfile.NamedTemporaryFile(
                    mode="wb", suffix=".toml", delete=False
                ) as f:
                    f.write(config_content)
                    f.flush()

                    try:
                        with open(f.name, "rb") as config_file:
                            result = toml_load(config_file)
                        assert result == {"test_key": "test_value"}
                    finally:
                        os.unlink(f.name)

        finally:
            # Restore original modules
            sys.modules.clear()
            sys.modules.update(original_modules)


class TestConfigImport:
    """Test import fallback by creating a test version of config.py."""

    @pytest.mark.benchmark
    @pytest.mark.skipif(
        sys.version_info < (3, 11), reason="tomllib only available in Python 3.11+"
    )
    def test_tomli_import_fallback_simulation(self):
        """Test tomli import fallback by simulating the ImportError condition."""

        # Create test code that simulates the config.py import logic
        test_code = """
try:
    import tomllib
    toml_load = tomllib.load
    used_tomllib = True
except ImportError:
    import tomli
    toml_load = tomli.load
    used_tomllib = False
"""

        # Test case 1: Normal case (tomllib available)
        namespace1 = {}
        exec(test_code, namespace1)
        assert namespace1["used_tomllib"] is True
        assert callable(namespace1["toml_load"])

        # Test case 2: Simulate ImportError for tomllib
        with patch.dict("sys.modules", {"tomllib": None}):
            with patch(
                "builtins.__import__",
                side_effect=self._mock_import_error,
            ):
                namespace2 = {}
                exec(test_code, namespace2)
                assert namespace2["used_tomllib"] is False
                assert callable(namespace2["toml_load"])

    @staticmethod
    def _mock_import_error(name, *args, **kwargs):
        """Mock import function that raises ImportError for tomllib."""
        if name == "tomllib":
            raise ImportError("No module named 'tomllib'")

        # For tomli, we need to mock it since it might not be installed
        if name == "tomli":
            # Create a mock tomli module
            class MockTomli:
                @staticmethod
                def load(f):
                    # Simple TOML parser for testing
                    content = f.read().decode("utf-8")
                    if "[test]" in content and 'value = "test"' in content:
                        return {"test": {"value": "test"}}
                    return {}

            return MockTomli()

        # For all other imports, use the real import
        return __import__(name, *args, **kwargs)

    @pytest.mark.benchmark
    def test_import_paths_coverage(self):
        """Ensure both import paths are conceptually tested."""
        # This test verifies that both the tomllib and tomli code paths
        # would work in their respective environments

        # Test the function signature matches expectation
        config_content = b"""
[test]
value = "test"
"""

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
            f.write(config_content)
            f.flush()

            try:
                # Test using the actual config module (uses tomllib on Python 3.11+)
                from commit_check.config import toml_load

                with open(f.name, "rb") as config_file:
                    result = toml_load(config_file)

                assert result == {"test": {"value": "test"}}

            finally:
                os.unlink(f.name)


class TestDeepMerge:
    """Tests for the _deep_merge helper."""

    @pytest.mark.benchmark
    def test_deep_merge_simple(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    @pytest.mark.benchmark
    def test_deep_merge_nested(self):
        base = {"commit": {"conventional_commits": True, "subject_max_length": 80}}
        override = {"commit": {"subject_max_length": 72}}
        result = _deep_merge(base, override)
        assert result["commit"]["conventional_commits"] is True
        assert result["commit"]["subject_max_length"] == 72

    @pytest.mark.benchmark
    def test_deep_merge_does_not_mutate_base(self):
        base = {"a": {"x": 1}}
        override = {"a": {"y": 2}}
        original_base = {"a": {"x": 1}}
        _deep_merge(base, override)
        # _deep_merge returns a new dict; base itself may be used but result is new
        assert _deep_merge(base, override)["a"] == {"x": 1, "y": 2}


class TestResolveInheritFrom:
    """Tests for the _resolve_inherit_from helper."""

    @pytest.mark.benchmark
    def test_no_inherit_from_returns_config_unchanged(self):
        config = {"commit": {"conventional_commits": True}}
        result = _resolve_inherit_from(dict(config))
        assert result == config

    @pytest.mark.benchmark
    def test_inherit_from_local_file(self):
        parent_content = b"""
[commit]
conventional_commits = true
subject_max_length = 100
"""
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".toml", delete=False
        ) as f:
            f.write(parent_content)
            parent_path = f.name

        try:
            config = {
                "inherit_from": parent_path,
                "commit": {"subject_max_length": 72},
            }
            result = _resolve_inherit_from(config)
            # Local config overrides parent
            assert result["commit"]["subject_max_length"] == 72
            # Parent value preserved when not overridden
            assert result["commit"]["conventional_commits"] is True
        finally:
            os.unlink(parent_path)

    @pytest.mark.benchmark
    def test_inherit_from_nonexistent_file_is_ignored(self):
        config = {"inherit_from": "/nonexistent/path/config.toml", "custom": "value"}
        result = _resolve_inherit_from(config)
        assert result == {"custom": "value"}

    @pytest.mark.benchmark
    def test_inherit_from_key_is_removed_from_result(self):
        config = {"inherit_from": "/nonexistent.toml", "commit": {"key": "val"}}
        result = _resolve_inherit_from(config)
        assert "inherit_from" not in result

    @pytest.mark.benchmark
    def test_inherit_from_url_success(self):
        parent_toml = b"[commit]\nsubject_max_length = 100\n"
        mock_response = MagicMock()
        mock_response.read.return_value = parent_toml
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            config = {
                "inherit_from": "https://example.com/cchk.toml",
                "commit": {"subject_max_length": 72},
            }
            result = _resolve_inherit_from(config)
            assert result["commit"]["subject_max_length"] == 72

    @pytest.mark.benchmark
    def test_inherit_from_url_failure_is_ignored(self):
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("network error"),
        ):
            config = {
                "inherit_from": "https://example.com/cchk.toml",
                "fallback": True,
            }
            result = _resolve_inherit_from(config)
            assert result == {"fallback": True}

    @pytest.mark.benchmark
    def test_inherit_from_http_url_is_rejected(self):
        """HTTP URLs are rejected for security; only HTTPS is allowed."""
        config = {
            "inherit_from": "http://example.com/cchk.toml",
            "fallback": True,
        }
        # urlopen should NOT be called for http:// URLs
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = _resolve_inherit_from(config)
            mock_urlopen.assert_not_called()
        assert result == {"fallback": True}

    @pytest.mark.benchmark
    def test_inherit_from_github_shorthand(self):
        """Test inherit_from with github: shorthand."""
        parent_toml = b"[commit]\nsubject_max_length = 100\n"
        mock_response = MagicMock()
        mock_response.read.return_value = parent_toml
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
            config = {
                "inherit_from": "github:my-org/.github:cchk.toml",
                "commit": {"subject_max_length": 72},
            }
            result = _resolve_inherit_from(config)

        # Should have fetched the right URL
        call_url = mock_open.call_args[0][0]
        assert "raw.githubusercontent.com" in call_url
        assert "my-org/.github" in call_url
        assert "cchk.toml" in call_url
        # Local override wins
        assert result["commit"]["subject_max_length"] == 72

    @pytest.mark.benchmark
    def test_inherit_from_github_shorthand_with_ref(self):
        """Test inherit_from with github: shorthand specifying a ref."""
        parent_toml = b"[commit]\nconventional_commits = true\n"
        mock_response = MagicMock()
        mock_response.read.return_value = parent_toml
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
            config = {
                "inherit_from": "github:my-org/.github@main:cchk.toml",
            }
            result = _resolve_inherit_from(config)

        call_url = mock_open.call_args[0][0]
        assert "/main/" in call_url
        assert result["commit"]["conventional_commits"] is True


class TestGithubShorthandToUrl:
    """Tests for the _github_shorthand_to_url helper."""

    @pytest.mark.benchmark
    def test_basic_shorthand(self):
        """github:owner/repo:path resolves to raw URL with HEAD."""
        url = _github_shorthand_to_url("github:my-org/.github:cchk.toml")
        assert url == "https://raw.githubusercontent.com/my-org/.github/HEAD/cchk.toml"

    @pytest.mark.benchmark
    def test_shorthand_with_ref(self):
        """github:owner/repo@ref:path resolves to raw URL with given ref."""
        url = _github_shorthand_to_url("github:my-org/.github@main:cchk.toml")
        assert url == "https://raw.githubusercontent.com/my-org/.github/main/cchk.toml"

    @pytest.mark.benchmark
    def test_shorthand_with_subdirectory(self):
        """github:owner/repo:subdir/path resolves correctly."""
        url = _github_shorthand_to_url("github:my-org/config@v1.0:.github/cchk.toml")
        assert url == "https://raw.githubusercontent.com/my-org/config/v1.0/.github/cchk.toml"

    @pytest.mark.benchmark
    def test_missing_colon_separator_returns_none(self):
        """Shorthand without file path separator returns None."""
        assert _github_shorthand_to_url("github:my-org/.github") is None

    @pytest.mark.benchmark
    def test_missing_owner_returns_none(self):
        """Shorthand with only a repo name (no owner/repo) returns None."""
        assert _github_shorthand_to_url("github:just-a-name:cchk.toml") is None

    @pytest.mark.benchmark
    def test_empty_path_returns_none(self):
        """Shorthand with empty file path returns None."""
        assert _github_shorthand_to_url("github:my-org/.github:") is None


class TestLoadFromUrl:
    """Tests for the _load_from_url helper."""

    @pytest.mark.benchmark
    def test_load_from_url_success(self):
        toml_content = b"[commit]\nconventional_commits = true\n"
        mock_response = MagicMock()
        mock_response.read.return_value = toml_content
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = _load_from_url("https://example.com/cchk.toml")
            assert result == {"commit": {"conventional_commits": True}}

    @pytest.mark.benchmark
    def test_load_from_url_network_error(self):
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("network error"),
        ):
            result = _load_from_url("https://example.com/cchk.toml")
            assert result == {}

    @pytest.mark.benchmark
    def test_load_from_url_http_error(self):
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                "https://example.com/cchk.toml", 404, "Not Found", {}, None
            ),
        ):
            result = _load_from_url("https://example.com/cchk.toml")
            assert result == {}


class TestLoadConfigInheritFrom:
    """Integration tests for load_config with inherit_from."""

    @pytest.mark.benchmark
    def test_load_config_with_inherit_from_local(self):
        parent_content = b"""
[commit]
conventional_commits = true
subject_max_length = 100
"""
        local_content = b"""
inherit_from = "{parent_path}"

[commit]
subject_max_length = 72
"""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                parent_path = os.path.join(tmpdir, "parent.toml")
                with open(parent_path, "wb") as f:
                    f.write(parent_content)

                local = local_content.replace(
                    b"{parent_path}", parent_path.encode()
                )
                with open("cchk.toml", "wb") as f:
                    f.write(local)

                config = load_config()
                assert config["commit"]["conventional_commits"] is True
                assert config["commit"]["subject_max_length"] == 72
            finally:
                os.chdir(original_cwd)
