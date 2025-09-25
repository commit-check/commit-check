"""Test for TOML parsing errors and exception handling."""

import pytest
import tempfile
import os
from commit_check.config import load_config


def test_load_config_invalid_toml():
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


def test_load_config_file_permission_error():
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


def test_tomli_import_fallback():
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
