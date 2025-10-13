"""Direct test of the config import fallback using module manipulation."""

import sys
import tempfile
import os
import pytest
from unittest.mock import patch


@pytest.mark.benchmark
def test_config_tomli_fallback_direct():
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
            import commit_check.config as config

            # Test that it works
            config_content = b'test_key = "test_value"'
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".toml", delete=False
            ) as f:
                f.write(config_content)
                f.flush()

                try:
                    with open(f.name, "rb") as config_file:
                        result = config.toml_load(config_file)
                    assert result == {"test_key": "test_value"}
                finally:
                    os.unlink(f.name)

    finally:
        # Restore original modules
        sys.modules.clear()
        sys.modules.update(original_modules)
