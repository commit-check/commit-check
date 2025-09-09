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


def check_author(checks: list, check_type: str, stdin_text: Optional[str] = None) -> int:
    # If an explicit value is provided (stdin), validate it even if there are no commits
    if stdin_text is None and has_commits() is False:
        return PASS # pragma: no cover

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
