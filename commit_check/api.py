"""Public Python API for commit-check.

This module exposes a lightweight, import-friendly interface that AI agents,
automation scripts, and tooling can call **without spawning a subprocess**.
All functions return plain dicts so results are easy to serialise, log, or
forward to an LLM.

Typical usage::

    from commit_check.api import validate_message, validate_branch, validate_tag, validate_author

    result = validate_message("feat: add streaming support")
    if result["status"] == "fail":
        for check in result["checks"]:
            if check["status"] == "fail":
                print(check["error"])
                print(check["suggest"])

Return-value schema (all functions)::

    {
        "status": "pass" | "fail" | "skip",
        "warnings": <number of checks with status "warn">,
        "notices": [
            {
                "setting": "<the setting that is not in force, e.g. [files] max_size>",
                "message": "<what was wrong with it, as the CLI prints it>",
            },
            ...
        ],
        "checks": [
            {
                "check":   "<rule name>",
                "status":  "pass" | "fail" | "warn" | "skip",
                "value":   "<actual value that was checked>",
                "error":   "<error description>",
                "suggest": "<how to fix>",
                "fix":     "<the corrected value when the fix is unambiguous; else empty>",
                "reason":  "<why a skipped check did not run, when known; else empty>",
            },
            ...
        ]
    }

``"skip"`` means the rule never ran — the author is on an ``ignore_authors``
list, or there was nothing to check. It is deliberately not ``"pass"``: a
skipped rule validated nothing, and collapsing the two makes a bypassed
policy indistinguishable from an enforced one. The top-level ``status`` is
``"skip"`` only when *every* check skipped, or when no check ran at all; a
run with any real verdict reports ``"pass"`` or ``"fail"`` as before. Only
``"fail"`` is an error, so code branching on ``status == "fail"`` keeps
working unchanged.

``notices`` lists the settings in the ``config`` dict that are not in force,
such as a ``[files]`` value that cannot be used and so turns its rule off; it
is an empty list when there are none. The dict's keys are not checked
against the known settings, as the CLI checks a config file's: an unknown
key in it is ignored without a notice.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from commit_check.config import deep_merge
from commit_check.config_merger import get_default_config
from commit_check.engine import (
    CheckOutcome,
    ValidationContext,
    ValidationEngine,
    count_warnings,
    overall_status,
)
from commit_check.rule_builder import RuleBuilder
from commit_check.rules_catalog import BRANCH_CHECKS, MESSAGE_CHECKS

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_result(
    outcomes: list[CheckOutcome], notices: list[dict[str, str]]
) -> dict[str, Any]:
    """Convert a list of :class:`~commit_check.engine.CheckOutcome` into the
    public return-value dict."""
    return {
        "status": overall_status(o.status for o in outcomes),
        "warnings": count_warnings(o.status for o in outcomes),
        "notices": notices,
        "checks": [o.to_dict() for o in outcomes],
    }


def _combine(results: list[dict[str, Any]]) -> dict[str, Any]:
    """One result from several, for the calls that run more than one pass.

    Each pass builds its rules from the same config, so a notice about it
    comes back from every pass; it is listed once.
    """
    checks = [c for r in results for c in r["checks"]]
    notices: list[dict[str, str]] = []
    for r in results:
        notices.extend(n for n in r["notices"] if n not in notices)
    # Shared reducer, not a local "fail or else pass": a combined call in
    # which every nested check skipped is still a skip.
    return {
        "status": overall_status(c["status"] for c in checks),
        "warnings": count_warnings(c["status"] for c in checks),
        "notices": notices,
        "checks": checks,
    }


def _run_checks(
    check_names: Collection[str],
    context: ValidationContext,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Build rules, filter to *check_names*, run the engine, return result."""
    notices: list[dict[str, str]] = []
    rule_builder = RuleBuilder(config, notices)
    all_rules = rule_builder.build_all_rules()
    filtered = [r for r in all_rules if r.check in check_names]
    engine = ValidationEngine(filtered)
    outcomes = engine.validate_all_detailed(context)
    return _build_result(outcomes, notices)


def _merge_config(user_config: dict[str, Any] | None) -> dict[str, Any]:
    """Return the effective config: user overrides merged on top of defaults."""
    base = get_default_config()
    if user_config:
        deep_merge(base, user_config)
    return base


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_message(
    message: str,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a commit message string.

    :param message: The full commit message to validate (subject + optional body).
    :param config: Optional configuration dict in the same shape as ``cchk.toml``.
        If *None*, built-in defaults are used.  You can pass a partial dict to
        override only the keys you care about, e.g.
        ``{"commit": {"allow_commit_types": ["feat", "fix"]}}``.
    :returns: A dict with ``"status"`` (``"pass"``/``"fail"``/``"skip"``), a
        ``"warnings"`` count, ``"notices"`` (settings not in force) and
        ``"checks"`` (list of per-rule outcomes).

    Example::

        >>> from commit_check.api import validate_message
        >>> validate_message("feat: add streaming support")["status"]
        'pass'
        >>> validate_message("WIP bad message")["status"]
        'fail'
    """
    cfg = _merge_config(config)
    context = ValidationContext(stdin_text=message.strip(), config=cfg)
    return _run_checks(MESSAGE_CHECKS, context, cfg)


def validate_branch(
    branch: str | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a branch name.

    :param branch: Branch name to validate.  If *None*, the current git branch
        is used (via ``git branch --show-current``).
    :param config: Optional configuration override dict.
    :returns: A dict with ``"status"``, a ``"warnings"`` count, ``"notices"``
        and ``"checks"``.

    Example::

        >>> from commit_check.api import validate_branch
        >>> validate_branch("feature/add-json-output")["status"]
        'pass'
        >>> validate_branch("bad_branch_name")["status"]
        'fail'
    """
    cfg = _merge_config(config)
    # Pass branch via stdin_text so BranchValidator picks it up without calling
    # git.  When branch is None the validator will fall back to git itself.
    context = ValidationContext(
        stdin_text=branch.strip() if branch else None,
        config=cfg,
    )
    return _run_checks(BRANCH_CHECKS, context, cfg)


def validate_tag(
    tag: str | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a tag name.

    :param tag: Tag name to validate. Multiple tags can be passed one per
        line. If *None*, the tags pointing at ``HEAD`` are used (via
        ``git tag --points-at``); a commit with no tag reports ``"skip"``.
    :param config: Optional configuration override dict. The pattern comes
        from ``config["tag"]["regex"]`` and defaults to SemVer with an
        optional leading ``v`` (``v1.2.3`` or ``1.2.3``).
    :returns: A dict with ``"status"``, a ``"warnings"`` count, ``"notices"``
        and ``"checks"``.

    Example::

        >>> from commit_check.api import validate_tag
        >>> validate_tag("v1.2.3")["status"]
        'pass'
        >>> validate_tag("release-candidate")["status"]
        'fail'
    """
    cfg = _merge_config(config)
    # Pass the tag via stdin_text so TagValidator picks it up without calling
    # git. Only None falls back to git: an explicit empty string names an
    # empty tag list, which skips rather than reading HEAD behind the
    # caller's back.
    context = ValidationContext(
        stdin_text=tag.strip() if tag is not None else None,
        config=cfg,
    )
    return _run_checks(["tag"], context, cfg)


def validate_push(
    push_refs: str | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate that a push is not a force push.

    :param push_refs: Push ref information in the format produced by git's
        pre-push hook: ``<local ref> <local sha1> <remote ref> <remote sha1>``,
        one entry per line.  If *None* or empty, or no line names a ref,
        there is nothing to compare and the check reports ``"skip"``.
    :param config: Optional configuration override dict.  The push check is
        always enabled when calling this function; a detected force push fails
        the result unless ``no_force_push`` is listed under ``warn``, in which
        case the check reports ``"warn"`` and the result passes.
    :returns: A dict with ``"status"`` (``"pass"``/``"fail"``/``"skip"``), a
        ``"warnings"`` count, ``"notices"`` and ``"checks"``.

    Example::

        >>> from commit_check.api import validate_push
        >>> zero = "0000000000000000000000000000000000000000"
        >>> result = validate_push(f"refs/heads/main abc123 refs/heads/main {zero}")
        >>> result["status"]
        'pass'
        >>> validate_push(None)["status"]
        'skip'
    """
    cfg = _merge_config(config)
    # Enable force push blocking in the config so the rule is built
    if "push" not in cfg:
        cfg["push"] = {}
    cfg["push"]["allow_force_push"] = False
    context = ValidationContext(stdin_text=push_refs, config=cfg)
    return _run_checks(["no_force_push"], context, cfg)


def validate_author(
    name: str | None = None,
    email: str | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate commit author name and/or email.

    :param name: Author name to validate.  If *None*, the value from
        ``git config user.name`` is used.
    :param email: Author email to validate.  If *None*, the value from
        ``git config user.email`` is used.
    :param config: Optional configuration override dict.
    :returns: A dict with ``"status"``, a ``"warnings"`` count, ``"notices"``
        and ``"checks"``.

    Example::

        >>> from commit_check.api import validate_author
        >>> validate_author(name="Ada Lovelace", email="ada@example.com")["status"]
        'pass'
    """
    cfg = _merge_config(config)
    checks: list[str] = []
    if name is not None:
        checks.append("author_name")
    if email is not None:
        checks.append("author_email")
    if not checks:
        # Validate both from git config
        checks = ["author_name", "author_email"]

    # AuthorValidator reads from git config / git log when stdin_text is None.
    # For an explicit single value we can only validate one at a time, so we
    # run separate passes when both are supplied.
    if name is not None and email is not None:
        name_result = _run_checks(
            ["author_name"],
            ValidationContext(stdin_text=name.strip(), config=cfg),
            cfg,
        )
        email_result = _run_checks(
            ["author_email"],
            ValidationContext(stdin_text=email.strip(), config=cfg),
            cfg,
        )
        return _combine([name_result, email_result])

    stdin = None
    if name is not None:
        stdin = name.strip()
    elif email is not None:
        stdin = email.strip()

    context = ValidationContext(stdin_text=stdin, config=cfg)
    return _run_checks(checks, context, cfg)


def validate_all(
    message: str | None = None,
    branch: str | None = None,
    author_name: str | None = None,
    author_email: str | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run all requested validations and return a combined result.

    This is the high-level entry point that mirrors the CLI ``commit-check -m -b``
    invocation but returns structured data instead of printing to the terminal.

    :param message: Commit message string to validate, or *None* to skip.
    :param branch: Branch name to validate, or *None* to skip.
    :param author_name: Author name to validate, or *None* to skip.
    :param author_email: Author email to validate, or *None* to skip.
    :param config: Optional configuration override dict.
    :returns: A dict with ``"status"``, a ``"warnings"`` count, ``"notices"``
        and ``"checks"``, combining all requested validations. A notice that
        more than one of them raised is listed once.

    Example::

        >>> from commit_check.api import validate_all
        >>> result = validate_all(
        ...     message="feat: implement new feature",
        ...     branch="feature/new-feature",
        ... )
        >>> result["status"]
        'pass'
    """
    results: list[dict[str, Any]] = []

    if message is not None:
        results.append(validate_message(message, config=config))

    if branch is not None:
        results.append(validate_branch(branch, config=config))

    if author_name is not None or author_email is not None:
        results.append(validate_author(author_name, author_email, config=config))

    return _combine(results)
