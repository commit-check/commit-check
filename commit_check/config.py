"""TOML config loader and schema for commit-check."""

from typing import Any, Dict
from pathlib import Path

try:
    import tomllib

    toml_load = tomllib.load
except ImportError:
    import tomli  # type: ignore

    toml_load = tomli.load

DEFAULT_CONFIG_PATHS = [
    Path("cchk.toml"),
    Path("commit-check.toml"),
]


def load_config(path_hint: str = "") -> Dict[str, Any]:
    """Load and validate config from TOML file."""
    if path_hint:
        p = Path(path_hint)
        if p.exists():
            with open(p, "rb") as f:
                return toml_load(f)
    for candidate in DEFAULT_CONFIG_PATHS:
        if candidate.exists():
            with open(candidate, "rb") as f:
                return toml_load(f)
    raise FileNotFoundError("No config file found (cchk.toml or commit-check.toml)")
