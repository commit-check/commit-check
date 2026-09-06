"""TOML config loader and schema for commit-check."""

from __future__ import annotations
from typing import Any
from pathlib import Path
import sys
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


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge override into base, returning a new dict."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _github_shorthand_to_url(value: str) -> str | None:
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
    rest = value[len("github:") :]

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


class _HttpsOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow redirects only to HTTPS targets.

    ``urlopen`` follows an HTTPS-to-HTTP redirect by default, which would
    let a parent config be swapped in transit on the way to being merged
    into the policy. Any redirect off HTTPS is refused instead.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        if not newurl.startswith("https://"):
            raise urllib.error.URLError(
                f"redirect to a non-HTTPS URL refused: {newurl}"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _LazyOpener:
    """The HTTPS-only opener, built on first use.

    ``build_opener`` is not free, and most runs never fetch a parent config
    at all, so the cost is paid only by the run that does.
    """

    def __init__(self) -> None:
        self._opener: urllib.request.OpenerDirector | None = None

    @property
    def handlers(self) -> list[urllib.request.BaseHandler]:
        return list(getattr(self._get(), "handlers"))

    def _get(self) -> urllib.request.OpenerDirector:
        if self._opener is None:
            self._opener = urllib.request.build_opener(_HttpsOnlyRedirectHandler())
        return self._opener

    def open(self, url: str, timeout: float = 10):  # type: ignore[no-untyped-def]
        return self._get().open(url, timeout=timeout)


_opener = _LazyOpener()


def _load_from_url(url: str) -> dict[str, Any]:
    """Load TOML config from an HTTPS URL.

    :param url: HTTPS URL pointing to a TOML config file.
    :returns: Parsed config dict.
    :raises ValueError: If the URL does not use HTTPS, or the fetched body is
        not valid TOML (``TOMLDecodeError``).
    :raises OSError: If the URL cannot be fetched, or redirects off HTTPS
        (``urllib.error.URLError`` is an ``OSError``).
    """
    if not url.startswith("https://"):
        raise ValueError("only https:// URLs are accepted")
    with _opener.open(url, timeout=10) as response:  # noqa: S310
        data = response.read()
    import io

    return toml_load(io.BytesIO(data))


def _load_parent_config(inherit_from: str) -> dict[str, Any]:
    """Load the parent config named by an ``inherit_from`` value.

    :raises ValueError: For a malformed ``github:`` shorthand, a non-HTTPS URL,
        or a parent that is not valid TOML (``TOMLDecodeError``).
    :raises OSError: For an unreachable URL or an unreadable local file.
    """
    if inherit_from.startswith("github:"):
        url = _github_shorthand_to_url(inherit_from)
        if url is None:
            raise ValueError('expected "github:owner/repo[@ref]:path/to/file.toml"')
        return _load_from_url(url)
    if inherit_from.startswith(("https://", "http://")):
        return _load_from_url(inherit_from)
    with open(Path(inherit_from), "rb") as f:
        return toml_load(f)


def _resolve_inherit_from(config: dict[str, Any]) -> dict[str, Any]:
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

    # Fail open, as documented: a parent that cannot be loaded leaves the
    # local config in force. Say so on stderr rather than silently, and keep
    # stdout clean for --format json.
    # TOMLDecodeError (tomllib and tomli alike) is a ValueError; URLError is
    # an OSError.
    try:
        parent = _load_parent_config(inherit_from)
    except (OSError, ValueError) as e:
        print(
            f'⊘ inherit_from "{inherit_from}" could not be loaded: {e}; '
            "continuing with the local config",
            file=sys.stderr,
        )
        parent = {}

    if parent:
        return _deep_merge(parent, config)
    return config


def load_config(path_hint: str = "") -> dict[str, Any]:
    """Load and validate config from TOML file.

    Supports ``inherit_from`` at the top level to merge an organization-level
    configuration from a local file path, a ``github:`` shorthand, or an HTTPS
    URL before applying local overrides.
    """
    if path_hint:
        p = Path(path_hint).resolve()
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
