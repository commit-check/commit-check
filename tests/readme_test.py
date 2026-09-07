"""The README's configuration reference must name every setting the tool has.

The table is static Markdown, so nothing regenerates it; this is what keeps a
new key in ``get_default_config()`` from going undocumented.
"""

from pathlib import Path

import pytest

from commit_check.config_merger import ConfigMerger, get_default_config

README = Path(__file__).resolve().parent.parent / "README.md"


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README.read_text(encoding="utf-8")


def _default_keys() -> list[str]:
    return [
        f"{section}.{key}"
        for section, keys in get_default_config().items()
        for key in keys
    ]


@pytest.mark.parametrize("dotted_key", _default_keys())
def test_every_default_key_is_in_readme(readme_text, dotted_key):
    """Each ``section.key`` from the defaults appears as a table row."""
    assert f"| `{dotted_key}` |" in readme_text, (
        f"{dotted_key} is missing from the README configuration reference"
    )


def _table_row(readme_text: str, dotted_key: str) -> str:
    """The configuration-reference row for ``dotted_key`` (empty if absent)."""
    prefix = f"| `{dotted_key}` |"
    return next(
        (line for line in readme_text.splitlines() if line.startswith(prefix)), ""
    )


@pytest.mark.parametrize("env_var", sorted(ConfigMerger.ENV_VAR_MAPPING))
def test_every_env_var_is_in_readme(readme_text, env_var):
    """Each ``CCHK_*`` variable is documented on the row of the key it sets."""
    section, key, _parser = ConfigMerger.ENV_VAR_MAPPING[env_var]
    row = _table_row(readme_text, f"{section}.{key}")
    assert f"`{env_var}`" in row, (
        f"{env_var} is missing from the README row for {section}.{key}"
    )


def test_top_level_warn_is_in_readme(readme_text):
    """``warn`` is not in the defaults dict, so it is checked by name."""
    assert "| `warn` (top level) |" in readme_text
