"""Fuzz the commit message and branch name checks with Atheris.

Feeds random text to the public API and to the AI signature scanner, which
parse untrusted input with regular expressions. Any exception is a bug.

Run locally (not part of CI):

    pip install atheris -e .
    python fuzz/fuzz_validate.py -max_total_time=60
"""

import sys

import atheris  # type: ignore[import-not-found, import-untyped]

with atheris.instrument_imports():
    from commit_check.ai_signatures import detect_ai_signatures
    from commit_check.api import validate_branch, validate_message


def TestOneInput(data: bytes) -> None:
    text = atheris.FuzzedDataProvider(data).ConsumeUnicodeNoSurrogates(4096)
    validate_message(text)
    detect_ai_signatures(text)
    # An empty branch name makes validate_branch ask git for the current one.
    if text.strip():
        validate_branch(text)


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
