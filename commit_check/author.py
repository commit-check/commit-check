"""Check git author name and email"""
import re
from typing import Optional
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import (
    get_commit_info,
    has_commits,
    print_error_header,
    print_error_message,
    print_suggestion,
)


_AUTHOR_FORMAT_MAP = {
    "author_name": "an",
    "author_email": "ae",
}


def _find_check(checks: list, check_type: str) -> Optional[dict]:
    """Return the first check dict matching check_type, else None."""
    for check in checks:
        if check.get("check") == check_type:
            return check
    return None


def _get_author_value(check_type: str) -> str:
    """Fetch the author value from git for the given check type."""
    format_str = _AUTHOR_FORMAT_MAP.get(check_type, "")
    return str(get_commit_info(format_str))


def _evaluate_check(check: dict, value: str) -> int:
    """Evaluate a single author check against the provided value."""
    regex = check.get("regex", "")
    if regex == "":
        print(f"{YELLOW}Not found regex for {check.get('check')}. skip checking.{RESET_COLOR}")
        return PASS

    if re.match(regex, value) is None:
        if not print_error_header.has_been_called:
            print_error_header()
        check_name = str(check.get("check", ""))
        error_msg = str(check.get("error", ""))
        print_error_message(check_name, regex, error_msg, value)
        if check.get("suggest"):
            print_suggestion(check["suggest"])
        return FAIL
    return PASS


def check_author(checks: list, check_type: str) -> int:
    """Validate author name or email according to configured regex."""
    if has_commits() is False:
        return PASS  # pragma: no cover

    check = _find_check(checks, check_type)
    if not check:
        return PASS

    # If regex is empty, skip without fetching author info
    regex = check.get("regex", "")
    if regex == "":
        print(f"{YELLOW}Not found regex for {check_type}. skip checking.{RESET_COLOR}")
        return PASS

    value = _get_author_value(check_type)
    return _evaluate_check(check, value)
