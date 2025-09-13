"""Check git author name and email"""

import re
from typing import Optional
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import (
    get_commit_info,
    has_commits,
    _find_check,
    _print_failure,
)


_AUTHOR_FORMAT_MAP = {
    "author_name": "an",
    "author_email": "ae",
}


def _get_author_value(check_type: str) -> str:
    """Fetch the author value from git for the given check type."""
    format_str = _AUTHOR_FORMAT_MAP.get(check_type, "")
    return str(get_commit_info(format_str))


def check_author(
    checks: list, check_type: str, stdin_text: Optional[str] = None
) -> int:
    # If an explicit value is provided (stdin), validate it even if there are no commits
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover

    check = _find_check(checks, check_type)
    if not check:
        return PASS

    # If regex is empty, skip without fetching author info
    regex = check.get("regex", "")
    if regex == "":
        print(f"{YELLOW}Not found regex for {check_type}. skip checking.{RESET_COLOR}")
        return PASS

    if stdin_text is not None:
        value = stdin_text
    else:
        value = _get_author_value(check_type)

    if re.match(regex, value):
        return PASS

    _print_failure(check, regex, value)

    return FAIL


# --- Additional per-option checks ---


def check_allow_authors(
    checks: list, check_type: str, stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover
    check = _find_check(checks, "allow_authors")
    if not check:
        return PASS
    allowed = set(check.get("allowed") or [])
    value = stdin_text if stdin_text is not None else _get_author_value(check_type)
    if value in allowed:
        return PASS
    _print_failure(check, f"allowed={sorted(allowed)}", value)
    return FAIL


def check_ignore_authors(
    checks: list, check_type: str, stdin_text: Optional[str] = None
) -> int:
    if stdin_text is None and has_commits() is False:
        return PASS  # pragma: no cover
    rule = _find_check(checks, "ignore_authors")
    if not rule:
        return PASS
    ignored = set(rule.get("ignored") or [])
    value = stdin_text if stdin_text is not None else _get_author_value(check_type)
    if value in ignored:
        return PASS
    return PASS  # ignore list only whitelists, no failure


def check_required_signoff_details(
    checks: list, commit_msg_file: str = "", stdin_text: Optional[str] = None
) -> int:
    """If configured, ensure signoff includes specific name/email."""
    # Reuse existing signoff check result; only apply extra constraints if present
    base = _find_check(checks, "commit_signoff")
    if not base:
        return PASS
    required_name = base.get("required_name")
    required_email = base.get("required_email")
    if not (required_name or required_email):
        return PASS
    # Read commit message (stdin_text here is the full commit message)
    msg = stdin_text if stdin_text is not None else get_commit_info("b")
    trailer = "Signed-off-by:" in msg
    if not trailer:
        return PASS  # let the main signoff check handle failure
    ok = True
    if required_name and required_name not in msg:
        ok = False
    if required_email and required_email not in msg:
        ok = False
    if ok:
        return PASS
    _print_failure(
        base, "required signoff details", required_name or required_email or ""
    )
    return FAIL
