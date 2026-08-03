"""Tests for stable rule IDs in the rules catalog."""

import re
from pathlib import Path
from typing import Any

import pytest

from commit_check.rules_catalog import (
    ALL_RULES,
    RULES_BY_CHECK,
    BRANCH_RULES,
    COMMIT_RULES,
    PUSH_RULES,
    RULES_DOCS_URL,
    RuleCatalogEntry,
)
from commit_check.rule_builder import RuleBuilder
from commit_check.config_merger import get_default_config

ALL_ENTRIES = [*COMMIT_RULES, *BRANCH_RULES, *PUSH_RULES]


class TestRuleIds:
    """The rule ID contract: stable, unique, well-formed."""

    @pytest.mark.benchmark
    def test_rule_ids_are_unique(self):
        """No two rules may share an ID."""
        ids = [e.rule_id for e in ALL_ENTRIES if e.rule_id]
        assert len(ids) == len(set(ids)), "duplicate rule IDs found"

    @pytest.mark.benchmark
    def test_identified_checks_are_unique(self):
        """Check names of identified rules must be unique.

        Rule identity is looked up by check name, so a duplicate would
        silently shadow one of the rules.
        """
        checks = [e.check for e in ALL_RULES]
        assert len(checks) == len(set(checks))
        assert len(RULES_BY_CHECK) == len(ALL_RULES)

    @pytest.mark.benchmark
    def test_rule_ids_are_well_formed(self):
        """Rule IDs look like CC001."""
        for entry in ALL_ENTRIES:
            if entry.rule_id:
                assert re.fullmatch(r"CC\d{3}", entry.rule_id), entry.rule_id

    @pytest.mark.benchmark
    def test_diagnostic_rules_all_have_ids(self):
        """Any rule that can report a failure must have an ID.

        Entries without an error message are internal bookkeeping (e.g.
        ``ignore_authors``) and intentionally carry no ID.
        """
        for entry in ALL_ENTRIES:
            if entry.error:
                assert entry.rule_id, f"{entry.check} can fail but has no rule ID"

    @pytest.mark.benchmark
    def test_docs_url_derives_from_id(self):
        """The docs URL is derived from the rule ID, not stored separately."""
        entry = RuleCatalogEntry(check="subject_imperative", rule_id="CC003")
        assert entry.docs_url == f"{RULES_DOCS_URL}#cc003"

    @pytest.mark.benchmark
    def test_no_docs_url_without_id(self):
        """An entry without a rule ID has no docs URL to link to."""
        assert RuleCatalogEntry(check="ignore_authors").docs_url is None

    @pytest.mark.benchmark
    def test_name_is_kebab_case(self):
        """The display name is the kebab-case form of the config key."""
        assert RuleCatalogEntry(check="subject_imperative").name == "subject-imperative"


class TestRuleIdPropagation:
    """Built rules carry their catalog identity through to output."""

    @pytest.mark.benchmark
    def test_built_rule_has_id_and_docs_url(self):
        """A rule built from the catalog carries its ID and docs URL."""
        rules = RuleBuilder({"commit": {"subject_imperative": True}}).build_all_rules()
        rule = next(r for r in rules if r.check == "subject_imperative")
        assert rule.rule_id == "CC003"
        assert rule.docs_url == f"{RULES_DOCS_URL}#cc003"

    @pytest.mark.benchmark
    def test_to_dict_includes_id_and_docs_url(self):
        """Serialised rules expose the ID and docs URL to consumers."""
        rules = RuleBuilder({"commit": {"subject_imperative": True}}).build_all_rules()
        rule = next(r for r in rules if r.check == "subject_imperative")
        as_dict = rule.to_dict()
        assert as_dict["rule_id"] == "CC003"
        assert as_dict["docs_url"].endswith("#cc003")

    @pytest.mark.benchmark
    def test_internal_entries_have_no_id(self):
        """ignore_authors is bookkeeping - it must not leak a rule ID."""
        entry = next(e for e in ALL_ENTRIES if e.check == "ignore_authors")
        assert entry.rule_id is None

        rules = RuleBuilder({"commit": {"ignore_authors": ["bot"]}}).build_all_rules()
        rule = next(r for r in rules if r.check == "ignore_authors")
        assert rule.rule_id is None
        assert rule.docs_url is None


class TestRulesDocumentation:
    """Anti-drift guard: every documented rule stays documented."""

    @pytest.mark.benchmark
    def test_every_rule_is_documented(self):
        """Each rule ID must have an anchor in the rules reference page.

        This prevents shipping a new rule without documenting it.
        """
        content = _read_doc("rules.rst")
        for entry in ALL_RULES:
            anchor = f".. _{entry.rule_id.lower()}:"
            assert anchor in content, (
                f"{entry.rule_id} ({entry.check}) is missing from docs/rules.rst"
            )

    @pytest.mark.benchmark
    def test_every_rule_has_a_section_heading(self):
        """Each rule needs a ``name (CCxxx)`` heading, not just an anchor.

        Checked inside the rule's own section: an anchor alone, or a heading
        that survives elsewhere on the page, would otherwise pass.
        """
        content = _read_doc("rules.rst")
        for entry in ALL_RULES:
            heading = f"{entry.name} ({entry.rule_id})"
            assert heading in _rule_section(content, entry.rule_id), (
                f"docs/rules.rst has no section titled '{heading}'"
            )

    @pytest.mark.benchmark
    def test_every_rule_explains_itself(self):
        """Each rule section must answer what it does and why it matters."""
        content = _read_doc("rules.rst")
        for entry in ALL_RULES:
            section = _rule_section(content, entry.rule_id)
            for required in ("**What it does**", "**Why is this bad?**", "**Options**"):
                assert required in section, (
                    f"{entry.rule_id} ({entry.check}) section is missing {required}"
                )


class TestDocumentedDefaults:
    """The documented defaults must match the ones the code actually uses."""

    @pytest.mark.benchmark
    def test_every_runtime_option_is_documented(self):
        """Every option the runtime defines has a row in the options table."""
        documented = _parse_options_table(_read_doc("configuration.rst"))
        for section, options in get_default_config().items():
            for option in options:
                assert (section, option) in documented, (
                    f"[{section}] {option} exists in get_default_config() but "
                    f"has no row in the options table of docs/configuration.rst"
                )

    @pytest.mark.benchmark
    def test_no_invented_options_are_documented(self):
        """The options table does not document options that do not exist."""
        runtime = get_default_config()
        for section, option in _parse_options_table(_read_doc("configuration.rst")):
            assert option in runtime.get(section, {}), (
                f"docs/configuration.rst documents [{section}] {option}, which "
                f"does not exist in get_default_config()"
            )

    @pytest.mark.benchmark
    def test_documented_defaults_match_the_runtime(self):
        """Every documented default equals the value the runtime actually uses.

        ``get_default_config()`` is what ``ConfigMerger.from_all_sources()``
        starts from, so it is the single source of truth for "what happens with
        no config file". The options table is maintained by hand and silently
        drifts away from it without this guard.
        """
        documented = _parse_options_table(_read_doc("configuration.rst"))
        runtime = get_default_config()

        for (section, option), (type_, cell) in sorted(documented.items()):
            if option not in runtime.get(section, {}):
                continue  # reported by test_no_invented_options_are_documented
            expected = runtime[section][option]
            actual = _documented_default(type_, cell)
            if isinstance(expected, list):
                # Allow-lists: order carries no meaning, membership does.
                assert set(actual or []) == set(expected), (
                    f"docs/configuration.rst documents [{section}] {option} "
                    f"with {sorted(set(actual or []) - set(expected))} that are "
                    f"not defaults, and is missing "
                    f"{sorted(set(expected) - set(actual or []))}"
                )
            else:
                assert actual == expected, (
                    f"docs/configuration.rst documents [{section}] {option} as "
                    f"{cell.strip()!r}, but the runtime default is {expected!r}"
                )


def _read_doc(name: str) -> str:
    """Read a file from the ``docs`` directory."""
    return (Path(__file__).parent.parent / "docs" / name).read_text(encoding="utf-8")


def _rule_section(content: str, rule_id: str) -> str:
    """Return just the part of the rules page belonging to one rule."""
    _, _, after = content.partition(f".. _{rule_id.lower()}:")
    return re.split(r"\n\.\. _cc\d{3}:", after)[0]


_OPTIONS_ROW = re.compile(
    r"\*\s+-\s+(commit|branch|push)\s*\n"  # section
    r"\s+-\s+(\w+)\s*\n"  # option name
    r"\s+-\s+(bool|int|str|list\[str\])\s*\n"  # type
    r"\s+-\s+(.+)\n"  # documented default
)


def _parse_options_table(content: str) -> dict[tuple[str, str], tuple[str, str]]:
    """Map ``(section, option) -> (type, raw default cell)``.

    Parses the five-cell ``list-table`` rows of the options table, e.g.::

        * - commit
          - subject_max_length
          - int
          - 80
          - Maximum length of the subject line.
    """
    return {
        (section, option): (type_, cell)
        for section, option, type_, cell in _OPTIONS_ROW.findall(content)
    }


_QUOTED = re.compile(r'^(?:``(.*?)``|"(.*?)")')


def _documented_default(type_: str, cell: str) -> Any:
    """Turn a documented default cell into a comparable Python value.

    Cells carry a human annotation after the value itself (``"" (disabled)``),
    so the value is read from the front of the cell and the rest ignored.
    """
    cell = cell.strip()
    if type_ == "bool":
        return cell.startswith("true")
    if type_ == "int":
        match = re.match(r"-?\d+", cell)
        return int(match.group()) if match else None
    if type_ == "list[str]":
        return re.findall(r'"(.*?)"', cell)
    quoted = _QUOTED.match(cell)
    if quoted is None:
        return cell
    # Group 1 is the ``literal`` form, group 2 the "literal" form; exactly one
    # of them matched.
    backticked, double_quoted = quoted.groups()
    return backticked if backticked is not None else double_quoted
