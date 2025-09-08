"""Check git author name and email"""
import re
from commit_check import YELLOW, RESET_COLOR, PASS, FAIL
from commit_check.util import (
    get_commit_info,
    has_commits,
    print_error_header,
    print_error_message,
    print_suggestion,
    _find_check,
)


_AUTHOR_FORMAT_MAP = {
    "author_name": "an",
    "author_email": "ae",
}


def _get_author_value(check_type: str) -> str:
    """Fetch the author value from git for the given check type."""
    format_str = _AUTHOR_FORMAT_MAP.get(check_type, "")
    return str(get_commit_info(format_str))


def _print_failure(check: dict, regex: str, actual: str) -> None:
    if not print_error_header.has_been_called:
        print_error_header()
    print_error_message(check['check'], regex, check['error'], actual)
    if check.get('suggest'):
        print_suggestion(check['suggest'])


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

    if re.match(regex, value):
        return PASS

    _print_failure(check, regex, value)

    return FAIL
