"""Tests for commit_check.__version__."""

import importlib
import pytest
from unittest.mock import patch
from importlib.metadata import PackageNotFoundError
import commit_check


class TestVersion:
    """Tests for __version__ resolution."""

    @pytest.mark.benchmark
    def test_version_is_string_when_installed(self):
        """When the package is installed, __version__ must be a non-empty string."""
        assert isinstance(commit_check.__version__, str)
        assert len(commit_check.__version__) > 0

    @pytest.mark.benchmark
    def test_version_fallback_when_not_installed(self):
        """When PackageNotFoundError is raised, __version__ must fall back to '0.0.0.dev'."""
        with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
            importlib.reload(commit_check)
            assert commit_check.__version__ == "0.0.0.dev"

        # Reload again to restore original version
        importlib.reload(commit_check)
        assert isinstance(commit_check.__version__, str)
