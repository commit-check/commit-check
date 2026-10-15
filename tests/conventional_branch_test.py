"""commit-check against the Conventional Branch specification's own test cases.

``conventional_branch_fixtures.json`` is ``tests/fixtures.json`` from
https://github.com/conventional-branch/conventional-branch at tag v1.1.0,
copied unchanged: each case is a branch name, whether the specification
accepts it, and why. When the specification publishes a new version, copy its
file over this one; a case that fails here is a place where commit-check and
the specification now disagree.

The default deliberately accepts more than the specification does: extra
types such as ``docs/`` and ``dependabot/``, and any description after the
``/``. So the default is held to accepting every name the specification
accepts, and ``require_description_grammar`` to agreeing on every case.
"""

import json
from pathlib import Path

import pytest

from commit_check.api import validate_branch

_FIXTURES = json.loads(
    (Path(__file__).parent / "conventional_branch_fixtures.json").read_text(
        encoding="utf-8"
    )
)
_CASES = _FIXTURES["cases"]
_VALID_CASES = [case for case in _CASES if case["valid"]]


def _case_id(case: dict) -> str:
    return case["branch"]


def test_the_fixtures_are_the_version_named_above():
    assert _FIXTURES["spec"] == "Conventional Branch"
    assert _FIXTURES["version"] == "1.1.0"


@pytest.mark.parametrize("case", _VALID_CASES, ids=_case_id)
def test_the_default_accepts_every_name_the_spec_accepts(case):
    result = validate_branch(case["branch"])
    assert result["status"] == "pass", case["reason"]


@pytest.mark.parametrize("case", _CASES, ids=_case_id)
def test_with_the_description_grammar_every_case_agrees(case):
    result = validate_branch(
        case["branch"], config={"branch": {"require_description_grammar": True}}
    )
    assert (result["status"] == "pass") is case["valid"], case["reason"]
