"""Startup cost: what importing the CLI may and may not do.

Every pre-commit hook, every commit the Action checks and every commit the
App checks starts a fresh interpreter, so import work is paid on each of
them. The benchmarks time test bodies in a process that has already imported
everything, so they cannot see it; these tests guard it instead.
"""

import json
import re
import subprocess
import sys

import pytest

from commit_check import ai_signatures, ai_signatures_data

# Imports the CLI entry point in a fresh interpreter and reports what that
# loaded: the heavy modules it pulled in, how many regexes it compiled, and
# whether any AI signature pattern was compiled.
_PROBE = """
import json, re, sys
compiled = 0
_compile = re._compile
def counting(*args, **kwargs):
    global compiled
    compiled += 1
    return _compile(*args, **kwargs)
re._compile = counting
import commit_check.main
from commit_check.ai_signatures_data import ALL_KNOWN_TOOLS
print(json.dumps({
    "modules": sorted(sys.modules),
    "compiled": compiled,
    "catalog_compiled": any(
        "regex" in vars(pattern) or "name_pattern" in vars(tool)
        for tool in ALL_KNOWN_TOOLS
        for pattern in tool.patterns
    ),
}))
"""

#: Regexes the CLI may compile at import. 29 when this was written; the AI
#: signature catalog alone was 160+ more. Raise it only for a pattern every
#: run needs.
MAX_IMPORT_COMPILES = 40


@pytest.fixture(scope="module")
def probe() -> dict:
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


class TestImportCost:
    @pytest.mark.parametrize(
        "module",
        [
            # Only --version needs the package metadata.
            "importlib.metadata",
            # Only an inherit_from URL needs the network stack.
            "urllib.request",
            "urllib.error",
            "http.client",
            "ssl",
        ],
    )
    def test_import_leaves_out(self, probe, module):
        assert module not in probe["modules"]

    def test_import_compiles_no_ai_signature(self, probe):
        """ai_attribution is off by default: the catalog compiles on first scan."""
        assert probe["catalog_compiled"] is False

    def test_import_compiles_few_regexes(self, probe):
        assert probe["compiled"] <= MAX_IMPORT_COMPILES, probe["compiled"]


class TestCatalogCompileCost:
    @pytest.mark.benchmark
    def test_compiling_the_catalog_cold(self):
        """What the first AI scan of a run pays; it grows with the catalog."""
        re.purge()
        ai_signatures.groups.cache_clear()
        ai_signatures._scans.cache_clear()
        ai_signatures._named_tools.cache_clear()
        for tool in ai_signatures_data.ALL_KNOWN_TOOLS:
            vars(tool).pop("name_pattern", None)
            for pattern in tool.patterns:
                vars(pattern).pop("regex", None)
        assert ai_signatures.has_ai_signature("x\n\nAssisted-by: Claude")
        assert ai_signatures.tool_named_in("Claude") == "Claude Code"
