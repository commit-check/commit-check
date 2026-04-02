"""TOML config loader and schema for commit-check."""

from typing import Any, Dict, Optional
from pathlib import Path
import urllib.request
import urllib.error

try:
    import tomllib

    toml_load = tomllib.load
except ImportError:
    import tomli  # type: ignore

    toml_load = tomli.load

DEFAULT_CONFIG_PATHS = [
    Path("cchk.toml"),
    Path("commit-check.toml"),
    Path(".github/cchk.toml"),
    Path(".github/commit-check.toml"),
]


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge override into base, returning a new dict."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _github_shorthand_to_url(value: str) -> Optional[str]:
    """Convert a ``github:`` shorthand to a raw GitHub content URL.

    Supported formats (modelled after Release Drafter's convention):

    * ``github:owner/repo:path/to/file.toml``
      → ``https://raw.githubusercontent.com/owner/repo/HEAD/path/to/file.toml``
    * ``github:owner/repo@ref:path/to/file.toml``
      → ``https://raw.githubusercontent.com/owner/repo/ref/path/to/file.toml``

    :param value: The raw ``inherit_from`` value starting with ``github:``.
    :returns: A resolved HTTPS URL, or ``None`` if the format is unrecognized.
    """
    # Strip the "github:" prefix
    rest = value[len("github:"):]

    # The path separator between repo spec and file path is ":"
    if ":" not in rest:
        return None

    repo_spec, file_path = rest.split(":", 1)
    if not repo_spec or not file_path:
        return None

    # Support optional ref via "@": "owner/repo@ref"
    if "@" in repo_spec:
        repo_part, ref = repo_spec.split("@", 1)
    else:
        repo_part, ref = repo_spec, "HEAD"

    if "/" not in repo_part:
        return None

    return f"https://raw.githubusercontent.com/{repo_part}/{ref}/{file_path}"


def _load_from_url(url: str) -> Dict[str, Any]:
    """Load TOML config from an HTTPS URL.

    :param url: HTTPS URL pointing to a TOML config file.
    :returns: Parsed config dict, or empty dict on failure.
    """
    try:
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
            data = response.read()
        import io

        return toml_load(io.BytesIO(data))
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        return {}


def _resolve_inherit_from(config: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve ``inherit_from`` directive, merging parent config with local.

    The ``inherit_from`` key at the top level of a config file may be:

    * A ``github:owner/repo:path`` shorthand (fetches via raw.githubusercontent.com)
    * An HTTPS URL pointing to a TOML config file
    * A local file path

    HTTP (non-TLS) URLs are rejected to prevent MITM attacks.  The parent
    config is loaded first; local settings override the parent.

    :param config: Already-parsed local TOML dict (may contain ``inherit_from``).
    :returns: Merged config with parent settings applied as base.
    """
    inherit_from = config.pop("inherit_from", None)
    if not inherit_from or not isinstance(inherit_from, str):
        return config

    parent: Dict[str, Any] = {}
    if inherit_from.startswith("github:"):
        url = _github_shorthand_to_url(inherit_from)
        if url:
            parent = _load_from_url(url)
    elif inherit_from.startswith("https://"):
        parent = _load_from_url(inherit_from)
    elif inherit_from.startswith("http://"):
        # Reject insecure HTTP to prevent MITM attacks when loading remote config
        pass
    else:
        parent_path = Path(inherit_from)
        if parent_path.exists():
            try:
                with open(parent_path, "rb") as f:
                    parent = toml_load(f)
            except Exception:
                parent = {}

    if parent:
        return _deep_merge(parent, config)
    return config


def load_config(path_hint: str = "") -> Dict[str, Any]:
    """Load and validate config from TOML file.

    Supports ``inherit_from`` at the top level to merge an organization-level
    configuration from a local file path, a ``github:`` shorthand, or an HTTPS
    URL before applying local overrides.
    """
    if path_hint:
        p = Path(path_hint)
        if not p.exists():
            raise FileNotFoundError(f"Specified config file not found: {path_hint}")
        with open(p, "rb") as f:
            config = toml_load(f)
        return _resolve_inherit_from(config)

    # Check default config paths only when no specific path is provided
    for candidate in DEFAULT_CONFIG_PATHS:
        if candidate.exists():
            with open(candidate, "rb") as f:
                config = toml_load(f)
            return _resolve_inherit_from(config)

    # Return empty config if no default config files found
    return {}
