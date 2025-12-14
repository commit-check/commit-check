"""Tests for commit_check.config module."""

import builtins
import pytest
import tempfile
import os
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


# Tests from config_edge_test.py
class TestConfigEdgeCases:
    """Test edge cases and error handling in config loading."""

    def test_load_config_invalid_toml(self, tmp_path):
        """Test loading config with invalid TOML syntax."""
        invalid_config = tmp_path / "invalid.toml"
        invalid_config.write_text("invalid toml [[[")

        with pytest.raises(Exception):  # Could be TOMLDecodeError or similar
            load_config(str(invalid_config))

    def test_load_config_file_permission_error(self, tmp_path, monkeypatch):
        """Test load_config when file cannot be read due to permissions."""
        config_file = tmp_path / "no_perms.toml"
        config_file.write_text("[commit-check]\nenabled = true")

        # Mock open to raise PermissionError
        original_open = builtins.open

        def mock_open(*args, **kwargs):
            if "no_perms.toml" in str(args[0]):
                raise PermissionError("Permission denied")
            return original_open(*args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)

        with pytest.raises(PermissionError):
            load_config(str(config_file))

    def test_tomli_import_fallback(self, monkeypatch):
        """Test tomli import fallback when tomllib not available."""
        import sys

        # Save original modules
        original_tomllib = sys.modules.get("tomllib")
        original_tomli = sys.modules.get("tomli")

        try:
            # Remove tomllib from sys.modules
            if "tomllib" in sys.modules:
                del sys.modules["tomllib"]

            # Force reimport of config module
            if "commit_check.config" in sys.modules:
                del sys.modules["commit_check.config"]

            # Mock tomllib to not exist
            monkeypatch.setitem(sys.modules, "tomllib", None)

            # Import should fall back to tomli
            from commit_check.config import toml_load

            assert toml_load is not None
        finally:
            # Restore original modules
            if original_tomllib is not None:
                sys.modules["tomllib"] = original_tomllib
            elif "tomllib" in sys.modules:
                del sys.modules["tomllib"]

            if original_tomli is not None:
                sys.modules["tomli"] = original_tomli
            elif "tomli" in sys.modules:
                del sys.modules["tomli"]

            # Force reimport of config module to restore original state
            if "commit_check.config" in sys.modules:
                del sys.modules["commit_check.config"]
            import commit_check.config  # noqa: F401


# Tests from config_fallback_test.py
class TestConfigTomllibFallback:
    """Test tomllib/tomli fallback mechanism."""

    def test_config_tomli_fallback_direct(self, tmp_path):
        """Test that config module can use tomli when tomllib is not available."""
        import sys

        # Save original modules
        original_tomllib = sys.modules.get("tomllib")
        original_tomli = sys.modules.get("tomli")
        original_config = sys.modules.get("commit_check.config")

        try:
            # Remove tomllib and config from sys.modules to force fresh import
            if "tomllib" in sys.modules:
                del sys.modules["tomllib"]
            if "commit_check.config" in sys.modules:
                del sys.modules["commit_check.config"]

            # Block tomllib import by setting it to None
            sys.modules["tomllib"] = None

            # Now import config - should fall back to tomli
            from commit_check.config import load_config, toml_load

            # Verify toml_load is available
            assert toml_load is not None

            # Test that config loading works with tomli
            config_file = tmp_path / "test.toml"
            config_file.write_text("[commit-check]\nenabled = true")

            result = load_config(str(config_file))
            assert result is not None
            assert "commit-check" in result
            assert result["commit-check"]["enabled"] is True

        finally:
            # Restore original modules
            if original_tomllib is not None:
                sys.modules["tomllib"] = original_tomllib
            elif "tomllib" in sys.modules:
                del sys.modules["tomllib"]

            if original_tomli is not None:
                sys.modules["tomli"] = original_tomli
            elif "tomli" in sys.modules:
                del sys.modules["tomli"]

            if original_config is not None:
                sys.modules["commit_check.config"] = original_config
            elif "commit_check.config" in sys.modules:
                del sys.modules["commit_check.config"]


# Tests from config_import_test.py
class TestConfigImportPaths:
    """Test import path coverage in config module."""

    def test_tomli_import_fallback_simulation(self, monkeypatch):
        """Test tomli import fallback by simulating tomllib unavailability."""
        import sys

        # Save original modules
        original_tomllib = sys.modules.get("tomllib")
        original_config = sys.modules.get("commit_check.config")

        try:
            # Remove modules to force fresh import
            if "tomllib" in sys.modules:
                del sys.modules["tomllib"]
            if "commit_check.config" in sys.modules:
                del sys.modules["commit_check.config"]

            # Simulate tomllib not being available by blocking its import
            import builtins

            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "tomllib":
                    raise ModuleNotFoundError("No module named 'tomllib'")
                return original_import(name, *args, **kwargs)

            monkeypatch.setattr(builtins, "__import__", mock_import)

            # Import config - should trigger tomli fallback
            from commit_check.config import toml_load

            # Verify toml_load is available (from tomli)
            assert toml_load is not None

        finally:
            # Restore original import
            monkeypatch.undo()

            # Restore original modules
            if original_tomllib is not None:
                sys.modules["tomllib"] = original_tomllib
            elif "tomllib" in sys.modules:
                del sys.modules["tomllib"]

            if original_config is not None:
                sys.modules["commit_check.config"] = original_config
            elif "commit_check.config" in sys.modules:
                del sys.modules["commit_check.config"]

    def test_import_paths_coverage(self):
        """Test various import paths in config module."""
        import sys

        # Save original modules
        original_tomllib = sys.modules.get("tomllib")
        original_tomli = sys.modules.get("tomli")
        original_config = sys.modules.get("commit_check.config")

        try:
            # Test 1: Import with tomllib available
            if "commit_check.config" in sys.modules:
                del sys.modules["commit_check.config"]

            from commit_check.config import toml_load as toml_load_1

            assert toml_load_1 is not None

            # Test 2: Force tomli fallback
            if "tomllib" in sys.modules:
                del sys.modules["tomllib"]
            if "commit_check.config" in sys.modules:
                del sys.modules["commit_check.config"]

            sys.modules["tomllib"] = None

            from commit_check.config import toml_load as toml_load_2

            assert toml_load_2 is not None

        finally:
            # Restore original modules
            if original_tomllib is not None:
                sys.modules["tomllib"] = original_tomllib
            elif "tomllib" in sys.modules:
                del sys.modules["tomllib"]

            if original_tomli is not None:
                sys.modules["tomli"] = original_tomli
            elif "tomli" in sys.modules:
                del sys.modules["tomli"]

            if original_config is not None:
                sys.modules["commit_check.config"] = original_config
            elif "commit_check.config" in sys.modules:
                del sys.modules["commit_check.config"]
