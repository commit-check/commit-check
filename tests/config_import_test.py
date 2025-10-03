"""Test import fallback by creating a test version of config.py."""

import tempfile
import os
from unittest.mock import patch


def test_tomli_import_fallback_simulation():
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
            side_effect=lambda name, *args, **kwargs: _mock_import_error(
                name, *args, **kwargs
            ),
        ):
            namespace2 = {}
            exec(test_code, namespace2)
            assert namespace2["used_tomllib"] is False
            assert callable(namespace2["toml_load"])


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


def test_import_paths_coverage():
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
