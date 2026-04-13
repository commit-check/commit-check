"""Public Python API for commit-check.

This module exposes a lightweight, import-friendly interface that AI agents,
automation scripts, and tooling can call **without spawning a subprocess**.
All functions return plain dicts so results are easy to serialise, log, or
forward to an LLM.

Typical usage::

    from commit_check.api import validate_message, validate_branch, validate_author

    result = validate_message("feat: add streaming support")
    if result["status"] == "fail":
        for check in result["checks"]:
            if check["status"] == "fail":
                print(check["error"])
                print(check["suggest"])

Return-value schema (all functions)::

    {
        "status": "pass" | "fail",
        "checks": [
            {
                "check":   "<rule name>",
                "status":  "pass" | "fail",
                "value":   "<actual value that was checked>",
                "error":   "<error description>",
                "suggest": "<how to fix>",
            },
            ...
        ]
    }
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

from commit_check.config_merger import get_default_config
from commit_check.engine import (
    CheckOutcome,
    ValidationContext,
    ValidationEngine,
)
from commit_check.rule_builder import RuleBuilder


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_result(outcomes: list[CheckOutcome]) -> Dict[str, Any]:
    """Convert a list of :class:`~commit_check.engine.CheckOutcome` into the
    public return-value dict."""
    overall = "fail" if any(o.status == "fail" for o in outcomes) else "pass"
    return {
        "status": overall,
        "checks": [o.to_dict() for o in outcomes],
    }


def _run_checks(
    check_names: list[str],
    context: ValidationContext,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Build rules, filter to *check_names*, run the engine, return result."""
    rule_builder = RuleBuilder(config)
    all_rules = rule_builder.build_all_rules()
    filtered = [r for r in all_rules if r.check in check_names]
    engine = ValidationEngine(filtered)
    outcomes = engine.validate_all_detailed(context)
    return _build_result(outcomes)


def _merge_config(user_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return the effective config: user overrides merged on top of defaults."""
    base = get_default_config()
    if user_config:
        from commit_check.config_merger import deep_merge

        # deep_copy the user config so that deep_merge cannot mutate the
        # caller's dict (deep_merge operates in-place on `base`, and may
        # assign nested objects from `override` directly into `base`).
        deep_merge(base, copy.deepcopy(user_config))
    return base


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_message(
    message: str,
    *,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate a commit message string.

    :param message: The full commit message to validate (subject + optional body).
    :param config: Optional configuration dict in the same shape as ``cchk.toml``.
        If *None*, built-in defaults are used.  You can pass a partial dict to
        override only the keys you care about, e.g.
        ``{"commit": {"allow_commit_types": ["feat", "fix"]}}``.
    :returns: A dict with ``"status"`` (``"pass"``/``"fail"``) and ``"checks"``
        (list of per-rule outcomes).

    Example::

        >>> from commit_check.api import validate_message
        >>> validate_message("feat: add streaming support")["status"]
        'pass'
        >>> validate_message("WIP bad message")["status"]
        'fail'
    """
    cfg = _merge_config(config)
    context = ValidationContext(stdin_text=message.strip(), config=cfg)
    check_names = [
        "message",
        "subject_imperative",
        "subject_max_length",
        "subject_min_length",
        "subject_capitalized",
        "require_signed_off_by",
        "require_body",
        "allow_merge_commits",
        "allow_revert_commits",
        "allow_empty_commits",
        "allow_fixup_commits",
        "allow_wip_commits",
    ]
    return _run_checks(check_names, context, cfg)


def validate_branch(
    branch: Optional[str] = None,
    *,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate a branch name.

    :param branch: Branch name to validate.  If *None*, the current git branch
        is used (via ``git branch --show-current``).
    :param config: Optional configuration override dict.
    :returns: A dict with ``"status"`` and ``"checks"``.

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
    return _run_checks(["branch", "merge_base"], context, cfg)


def validate_author(
    name: Optional[str] = None,
    email: Optional[str] = None,
    *,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate commit author name and/or email.

    :param name: Author name to validate.  If *None*, the value from
        ``git config user.name`` is used.
    :param email: Author email to validate.  If *None*, the value from
        ``git config user.email`` is used.
    :param config: Optional configuration override dict.
    :returns: A dict with ``"status"`` and ``"checks"``.

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
        all_checks = name_result["checks"] + email_result["checks"]
        overall = "fail" if any(c["status"] == "fail" for c in all_checks) else "pass"
        return {"status": overall, "checks": all_checks}

    stdin = None
    if name is not None:
        stdin = name.strip()
    elif email is not None:
        stdin = email.strip()

    context = ValidationContext(stdin_text=stdin, config=cfg)
    return _run_checks(checks, context, cfg)


def validate_push(
    push_refs: Optional[str] = None,
    *,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate that a push is not a force push.

    :param push_refs: Push ref information in the format produced by git's
        pre-push hook: ``<local ref> <local sha1> <remote ref> <remote sha1>``,
        one entry per line.  If *None*, the check is skipped (returns pass).
    :param config: Optional configuration override dict.  The push check is
        always enabled when calling this function; force pushes detected here
        will always return ``"fail"``.
    :returns: A dict with ``"status"`` (``"pass"``/``"fail"``) and ``"checks"``.

    Example::

        >>> from commit_check.api import validate_push
        >>> zero = "0000000000000000000000000000000000000000"
        >>> result = validate_push(f"refs/heads/main abc123 refs/heads/main {zero}")
        >>> result["status"]
        'pass'
    """
    cfg = _merge_config(config)
    # Enable force push blocking in the config so the rule is built
    if "push" not in cfg:
        cfg["push"] = {}
    cfg["push"]["allow_force_push"] = False
    context = ValidationContext(stdin_text=push_refs, config=cfg)
    return _run_checks(["no_force_push"], context, cfg)


def validate_all(
    message: Optional[str] = None,
    branch: Optional[str] = None,
    author_name: Optional[str] = None,
    author_email: Optional[str] = None,
    *,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run all requested validations and return a combined result.

    This is the high-level entry point that mirrors the CLI ``commit-check -m -b``
    invocation but returns structured data instead of printing to the terminal.

    :param message: Commit message string to validate, or *None* to skip.
    :param branch: Branch name to validate, or *None* to skip.
    :param author_name: Author name to validate, or *None* to skip.
    :param author_email: Author email to validate, or *None* to skip.
    :param config: Optional configuration override dict.
    :returns: A dict with ``"status"`` and ``"checks"`` combining all requested
        validations.

    Example::

        >>> from commit_check.api import validate_all
        >>> result = validate_all(
        ...     message="feat: implement new feature",
        ...     branch="feature/new-feature",
        ... )
        >>> result["status"]
        'pass'
    """
    all_checks: list[Dict[str, Any]] = []

    if message is not None:
        msg_result = validate_message(message, config=config)
        all_checks.extend(msg_result["checks"])

    if branch is not None:
        branch_result = validate_branch(branch, config=config)
        all_checks.extend(branch_result["checks"])

    if author_name is not None or author_email is not None:
        author_result = validate_author(author_name, author_email, config=config)
        all_checks.extend(author_result["checks"])

    overall = "fail" if any(c["status"] == "fail" for c in all_checks) else "pass"
    return {"status": overall, "checks": all_checks}
