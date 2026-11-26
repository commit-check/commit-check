"""Find risky settings in the agent config files a commit changes.

What to look for is data: ``agent_configs.toml`` beside this module lists,
per agent, the files it reads and the settings in them that the agent config
rules (CC601 to CC604) report. This module reads that list and matches file
contents against it; the validator in :mod:`commit_check.engine` feeds it
the files of the commits under test.

A setting is reported where it is committed, whoever wrote it: a project
file applies to everyone who opens the repository, and the agents' own
safeguards (a trust prompt, a first-run question) are a click away from
letting it through.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from functools import cache
from pathlib import Path
from typing import Any

#: The catalog of agents and their settings.
CATALOG_PATH = Path(__file__).with_name("agent_configs.toml")

#: The rule each catalog entry may name, kebab-case as the catalog writes
#: it, mapped to the check it reports under.
RULES = {
    "agent-mcp-auto-approve": "agent_mcp_auto_approve",
    "agent-api-endpoint": "agent_api_endpoint",
    "agent-full-access": "agent_full_access",
    "agent-unrestricted-trigger": "agent_unrestricted_trigger",
}

#: The ``[agent_config]`` list that lets a finding of each check through,
#: for the checks that have one. A server is let through by its name, an
#: endpoint by its URL.
ALLOWLISTS = {
    "agent_mcp_auto_approve": "allow_mcp_servers",
    "agent_api_endpoint": "allow_api_endpoints",
}

#: The formats a catalog file may be in, by file name ending.
_FORMATS = {".json": "json", ".toml": "toml", ".yml": "yaml", ".yaml": "yaml"}

#: Config files are small; anything bigger is not one and is not read.
MAX_FILE_SIZE = 1024 * 1024

_AGENT_KEYS = frozenset({"name", "files", "uses", "docs", "settings"})
_SETTING_KEYS = frozenset({"rule", "key", "value", "docs"})


class _Any:
    """The ``value`` of a setting whose every value is risky."""

    def __repr__(self) -> str:
        return "ANY"


ANY: Any = _Any()


@dataclass(frozen=True)
class AgentSetting:
    """One risky setting of one agent, from the catalog.

    :param agent: The agent's name.
    :param check: The check that reports it, e.g. ``agent_full_access``.
    :param files: Globs of the files it is read from.
    :param key: The setting's path, split on ``.``; ``*`` is any one key.
    :param value: The risky value, or :data:`ANY`.
    :param uses: For a YAML file, the action a step's ``uses:`` names;
        only that step's settings count.
    :param docs: Where the agent documents the setting.
    """

    agent: str
    check: str
    files: tuple[str, ...]
    key: tuple[str, ...]
    value: Any
    uses: str | None
    docs: str

    @property
    def key_text(self) -> str:
        return ".".join(self.key)

    def reads(self, path: str) -> bool:
        """Whether *path* is one of the files this setting is read from.

        A ``*`` stays within one directory, as it does in a shell:
        ``.github/workflows/*.yml`` is not ``.github/workflows/old/ci.yml``,
        which GitHub does not run.
        """
        depth = path.count("/")
        return any(
            depth == pattern.count("/") and fnmatchcase(path, pattern)
            for pattern in self.files
        )


@dataclass(frozen=True)
class Finding:
    """A risky setting found in a file.

    :param subject: What an allowlist names to let it through: the server's
        name or the endpoint's URL. ``None`` when nothing can, such as a
        setting that approves every server at once.
    """

    check: str
    path: str
    setting: str
    subject: str | None
    agent: str

    def __str__(self) -> str:
        return f"{self.setting} in {self.path}"


def _https_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("https://")


class CatalogError(ValueError):
    """An entry of ``agent_configs.toml`` that cannot be used."""


def parse_catalog(data: dict[str, Any]) -> tuple[AgentSetting, ...]:
    """The settings a parsed catalog lists, or :class:`CatalogError` naming
    the first entry that is not usable.

    The catalog is checked whole on load, so a mistake in a new entry fails
    the test suite rather than silently matching nothing.
    """
    agents = data.get("agent")
    if set(data) != {"agent"} or not isinstance(agents, list) or not agents:
        raise CatalogError("the catalog must hold [[agent]] tables and nothing else")
    settings: list[AgentSetting] = []
    for agent in agents:
        name = agent.get("name") if isinstance(agent, dict) else None
        if not isinstance(name, str) or not name.strip():
            raise CatalogError(f"an [[agent]] table has no name: {agent!r}")
        where = f"agent {name!r}"
        unknown = set(agent) - _AGENT_KEYS
        if unknown:
            raise CatalogError(f"{where}: unknown keys {sorted(unknown)}")
        files = agent.get("files")
        if not isinstance(files, list) or not files:
            raise CatalogError(f"{where}: files must be a list of paths")
        for pattern in files:
            if not isinstance(pattern, str) or _format(pattern) is None:
                raise CatalogError(
                    f"{where}: {pattern!r} is not a .json, .toml, .yml or .yaml path"
                )
        uses = agent.get("uses")
        if uses is not None and (not isinstance(uses, str) or not uses.strip()):
            raise CatalogError(f"{where}: uses must name the action")
        docs = agent.get("docs")
        if not _https_url(docs):
            raise CatalogError(f"{where}: docs must be an https:// link")
        entries = agent.get("settings")
        if not isinstance(entries, list) or not entries:
            raise CatalogError(f"{where}: settings must list at least one setting")
        for entry in entries:
            if not isinstance(entry, dict):
                raise CatalogError(f"{where}: a setting must be a table, got {entry!r}")
            unknown = set(entry) - _SETTING_KEYS
            if unknown:
                raise CatalogError(f"{where}: unknown setting keys {sorted(unknown)}")
            rule = entry.get("rule")
            if rule not in RULES:
                raise CatalogError(
                    f"{where}: rule {rule!r} is not one of {', '.join(RULES)}"
                )
            key = entry.get("key")
            parts = tuple(key.split(".")) if isinstance(key, str) else ()
            if not parts or not all(parts) or parts.count("*") > 1:
                raise CatalogError(
                    f"{where}: key {key!r} must be keys joined with '.', "
                    "with at most one '*'"
                )
            value = entry.get("value", ANY)
            if value is not ANY and not isinstance(value, (bool, int, str)):
                raise CatalogError(f"{where}: value of {key!r} must be one value")
            setting_docs = entry.get("docs", docs)
            if not _https_url(setting_docs):
                raise CatalogError(f"{where}: docs of {key!r} must be an https:// link")
            settings.append(
                AgentSetting(
                    agent=name,
                    check=RULES[rule],
                    files=tuple(files),
                    key=parts,
                    value=value,
                    uses=uses,
                    docs=setting_docs,
                )
            )
    return tuple(settings)


@cache
def load_settings() -> tuple[AgentSetting, ...]:
    """Every setting in the catalog, read from disk once per process."""
    with CATALOG_PATH.open("rb") as f:
        return parse_catalog(tomllib.load(f))


def _format(path: str) -> str | None:
    for ending, fmt in _FORMATS.items():
        if path.endswith(ending):
            return fmt
    return None


# A string or a comment: comments are dropped and strings kept as they are,
# so "//" inside a URL survives. One left open runs to the end of the text,
# so each character is read once: retrying a "/*" that never closes from
# every later "/*" would take time that grows with the square of the size.
# Left as text, not compiled at import: most runs read no JSON file that
# needs them.
_JSON_STRING = r'"(?:\\.|[^"\\])*(?:"|\\?\Z)'
_JSONC_TOKEN = rf"{_JSON_STRING}|//[^\n]*|/\*.*?(?:\*/|\Z)"
_TRAILING_COMMA = rf"{_JSON_STRING}|,(\s*[}}\]])"


def _loads_jsonc(text: str) -> Any:
    """JSON that may hold comments and trailing commas, as VS Code's does."""
    try:
        return json.loads(text)
    except ValueError:
        pass
    stripped = re.sub(
        _JSONC_TOKEN,
        lambda m: m.group(0) if m.group(0).startswith('"') else " ",
        text,
        flags=re.DOTALL,
    )
    stripped = re.sub(
        _TRAILING_COMMA,
        lambda m: m.group(1) if m.group(1) is not None else m.group(0),
        stripped,
    )
    return json.loads(stripped)


def _parse(fmt: str, text: str) -> Any:
    """The file's data, or ``None`` when it does not parse.

    A file its own agent could not read either holds no setting that
    takes effect, so it is not reported.
    """
    try:
        if fmt == "json":
            return _loads_jsonc(text)
        return tomllib.loads(text)
    except ValueError:
        return None


def _lookup(
    node: Any, keys: tuple[str, ...], name: str | None = None
) -> Iterator[tuple[str | None, tuple[str, ...], Any]]:
    """``(name, path, value)`` for each value at *keys* in *node*.

    *name* is the key ``*`` stood for, *path* the keys as found. A key that
    holds dots itself, as VS Code's ``chat.tools.autoApprove`` does, is
    tried whole as well as split: every run of keys that is present is
    followed, so a decoy ``"env.X"`` key cannot hide the ``env`` block
    beside it.
    """
    if not keys:
        yield name, (), node
        return
    if not isinstance(node, dict):
        return
    if keys[0] == "*":
        for key, value in node.items():
            for found_name, path, found in _lookup(value, keys[1:], key):
                yield found_name, (key, *path), found
        return
    stop = keys.index("*") if "*" in keys else len(keys)
    for end in range(stop, 0, -1):
        joined = ".".join(keys[:end])
        if joined in node:
            for found_name, path, found in _lookup(node[joined], keys[end:], name):
                yield found_name, (joined, *path), found


def _same(found: Any, value: Any) -> bool:
    # ``True == 1`` in Python; a setting's type is part of what it means.
    return type(found) is type(value) and found == value


def _show(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _structured_findings(
    path: str, data: Any, settings: Iterable[AgentSetting]
) -> Iterator[Finding]:
    for setting in settings:
        for name, keys, found in _lookup(data, setting.key):
            shown_key = ".".join(keys)
            items = found if isinstance(found, list) else [found]
            verb = "has" if isinstance(found, list) else "="
            if setting.value is ANY:
                for item in items:
                    if not item:
                        continue
                    subject = name
                    if subject is None and isinstance(item, str):
                        subject = item
                    yield Finding(
                        setting.check,
                        path,
                        f"{shown_key} {verb} {_show(item)}",
                        subject,
                        setting.agent,
                    )
            elif any(_same(item, setting.value) for item in items):
                yield Finding(
                    setting.check,
                    path,
                    f"{shown_key} {verb} {_show(setting.value)}",
                    name,
                    setting.agent,
                )


# YAML's double-quoted escapes, besides \x, \u and \U.
_YAML_ESCAPES = {
    "0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n",
    "v": "\v", "f": "\f", "r": "\r", "e": "\x1b", " ": " ", '"': '"',
    "/": "/", "\\": "\\", "N": "\x85", "_": "\xa0", "L": "\u2028",
    "P": "\u2029",
}  # fmt: skip
_YAML_ESCAPE = r"\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|.)"
_YAML_QUOTED = {'"': r'"((?:\\.|[^"\\])*)"', "'": r"'((?:''|[^'])*)'"}


def _yaml_unescape(match: re.Match[str]) -> str:
    code = match.group(1)
    if code[0] in "xuU" and len(code) > 1:
        point = int(code[1:], 16)
        return chr(point) if point <= 0x10FFFF else match.group(0)
    return _YAML_ESCAPES.get(code, match.group(0))


def _yaml_scalar(raw: str) -> str | None:
    """The value on a ``key: value`` line, unquoted, or ``None`` for one
    that starts a block, a mapping or a list on the lines below.

    A quoted value is read as YAML reads it, so ``"\\u002a"`` is ``*``.
    """
    raw = raw.strip()
    if raw[:1] in _YAML_QUOTED:
        quoted = re.match(_YAML_QUOTED[raw[0]], raw)
        if quoted is None:
            return None
        if raw[0] == "'":
            return quoted.group(1).replace("''", "'")
        return re.sub(_YAML_ESCAPE, _yaml_unescape, quoted.group(1))
    raw = re.split(r"\s#", raw, maxsplit=1)[0].strip()
    if not raw or raw[0] in "|>&*{[":
        return None
    return raw


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _steps_using(lines: list[str], uses: str) -> list[list[str]]:
    """The lines of each YAML step whose ``uses:`` names *uses*.

    A step runs from its ``-`` to the next line indented no deeper than
    that ``-``, so a setting of another step, another job's action or a
    comment that names the action is not taken for this one's.
    """
    pattern = re.compile(
        rf"^(?P<dash>\s*-\s+)?\s*uses\s*:\s*['\"]?{re.escape(uses)}(?:[@'\"\s]|$)"
    )
    steps = []
    for number, line in enumerate(lines):
        match = pattern.match(line)
        if not match:
            continue
        start = number
        if match.group("dash"):
            dash = _indent(line)
        else:
            # "uses:" under the step's "- name:" line: the step starts at the
            # nearest line above that begins with a "-" further left.
            dash = _indent(line) - 2
            while start > 0:
                start -= 1
                above = lines[start]
                if above.strip().startswith("-") and _indent(above) <= dash:
                    dash = _indent(above)
                    break
        end = number + 1
        while end < len(lines):
            stripped = lines[end].strip()
            if (
                stripped
                and not stripped.startswith("#")
                and _indent(lines[end]) <= dash
            ):
                break
            end += 1
        steps.append(lines[start:end])
    return steps


def _inputs(step: list[str]) -> list[str]:
    """The lines of a step's ``with:`` inputs, one input each.

    Lines nested deeper, such as those of a multi-line ``prompt``, are left
    out: text in a prompt is not a setting.
    """
    inputs: list[str] = []
    for number, line in enumerate(step):
        if not re.match(r"^\s*(?:-\s+)?with\s*:\s*(?:#.*)?$", line):
            continue
        column = len(line) - len(line.lstrip(" -"))
        depth = None
        for below in step[number + 1 :]:
            stripped = below.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = _indent(below)
            if indent <= column:
                break
            if depth is None:
                depth = indent
            if indent == depth:
                inputs.append(below)
    return inputs


def _yaml_findings(
    path: str, text: str, settings: Iterable[AgentSetting]
) -> Iterator[Finding]:
    lines = text.splitlines()
    for setting in settings:
        scopes = (
            [lines]
            if setting.uses is None
            else [_inputs(step) for step in _steps_using(lines, setting.uses)]
        )
        key = setting.key[-1]
        pattern = re.compile(
            rf"^\s*(?:-\s+)?(['\"]?){re.escape(key)}\1\s*:(?P<value>.*)$"
        )
        for line in (line for scope in scopes for line in scope):
            match = pattern.match(line)
            if not match:
                continue
            value = _yaml_scalar(match.group("value"))
            if value is None:
                continue
            if setting.value is ANY:
                yield Finding(
                    setting.check, path, f"{key} = {_show(value)}", value, setting.agent
                )
                continue
            expected = setting.value
            if isinstance(expected, bool):
                hit = value.lower() == str(expected).lower()
            else:
                hit = value == str(expected)
            if hit:
                yield Finding(
                    setting.check, path, f"{key} = {_show(value)}", None, setting.agent
                )


def find_settings(
    path: str, text: str, settings: Sequence[AgentSetting] | None = None
) -> list[Finding]:
    """The risky settings in *text*, the contents of the file at *path*.

    :param settings: The catalog entries to look for; the whole catalog
        when not given. Only those whose files include *path* are used.
    """
    if settings is None:
        settings = load_settings()
    relevant = [s for s in settings if s.reads(path)]
    if not relevant:
        return []
    # The catalog admits only files whose format is known.
    fmt = _format(path) or "json"
    if fmt == "yaml":
        found = _yaml_findings(path, text, relevant)
    else:
        data = _parse(fmt, text)
        if data is None:
            return []
        found = _structured_findings(path, data, relevant)
    return list(dict.fromkeys(found))


def is_allowed(finding: Finding, allowed: Iterable[str]) -> bool:
    """Whether an ``[agent_config]`` allowlist lets *finding* through.

    An endpoint matches with or without a trailing slash; anything else
    must match exactly. A URL is never matched by its start, which
    ``https://gateway.example.com.attacker.net`` would pass.
    """
    if finding.subject is None:
        return False
    if finding.check == "agent_api_endpoint":
        subject = finding.subject.rstrip("/")
        return any(subject == item.rstrip("/") for item in allowed)
    return finding.subject in allowed
