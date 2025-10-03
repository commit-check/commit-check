"""Tests for commit_check.config module."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch
from commit_check.config import load_config, DEFAULT_CONFIG_PATHS


class TestConfig:
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

    def test_load_config_with_nonexistent_path_hint(self):
        """Test loading config when path hint doesn't exist, falls back to default paths."""
        # Create a temporary cchk.toml in current directory
        config_content = b"""
[checks]
fallback = true
"""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                # Create cchk.toml in temp directory
                with open("cchk.toml", "wb") as f:
                    f.write(config_content)

                # Try to load with nonexistent path hint
                config = load_config("nonexistent.toml")
                assert "checks" in config
                assert config["checks"]["fallback"] is True
            finally:
                os.chdir(original_cwd)

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

    def test_load_config_file_not_found(self):
        """Test FileNotFoundError when no config files exist."""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                with pytest.raises(FileNotFoundError, match="No config file found"):
                    load_config()
            finally:
                os.chdir(original_cwd)

    def test_load_config_file_not_found_with_invalid_path_hint(self):
        """Test FileNotFoundError when path hint and default paths don't exist."""
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                with pytest.raises(FileNotFoundError, match="No config file found"):
                    load_config("nonexistent.toml")
            finally:
                os.chdir(original_cwd)

    def test_default_config_paths_constant(self):
        """Test that DEFAULT_CONFIG_PATHS contains expected paths."""
        assert len(DEFAULT_CONFIG_PATHS) == 2
        assert Path("cchk.toml") in DEFAULT_CONFIG_PATHS
        assert Path("commit-check.toml") in DEFAULT_CONFIG_PATHS

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
