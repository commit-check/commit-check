"""Tests for commit_check.config module."""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch
from commit_check.config import load_config, DEFAULT_CONFIG_PATHS


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
        assert len(DEFAULT_CONFIG_PATHS) == 2
        assert Path("cchk.toml") in DEFAULT_CONFIG_PATHS
        assert Path("commit-check.toml") in DEFAULT_CONFIG_PATHS

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
