# Contributing

Thank you for investing your time in contributing to our project! We welcome feedback, bug reports, and pull requests!

## New contributor guide

Our development branch is `main`. When submitting pull requests, please adhere to the following guidelines:

* Add tests for any new features and bug fixes.
* Put a reasonable amount of comments into the code.
* Fork [commit-check](https://github.com/commit-check/commit-check) on your GitHub user account.
* Create a branch from `main`, make your changes on the new branch, and then create a PR against the `main` branch of the commit-check repository.
* Separate unrelated changes into multiple pull requests for better review and management.

By contributing any code or documentation to this repository (by raising pull requests or otherwise), you explicitly agree to the [License Agreement](https://github.com/commit-check/commit-check/blob/main/LICENSE).

## Architecture

### Overview

Commit-check validates Git commit metadata using a pipeline of configurable validators. The key flow is:

```
CLI args / Env vars / TOML file
           │
           ▼
      ConfigMerger          ← Merges all config sources (priority: CLI > Env > TOML > Defaults)
           │
           ▼
       RuleBuilder           ← Builds ValidationRule objects from merged config + rules catalog
           │
           ▼
    ValidationEngine         ← Iterates over rules, picks the right validator for each
           │
           ▼
   BaseValidator subclasses  ← Each validator performs one focused check
           │
           ├─ (--fix flag) → CommitFixer ← Applies rule-driven transforms to fix violations
           │                               (imperative tense, capitalization, WIP strip, signoff)
           │                     │
           │                     ▼
           │             git commit --amend  ← or write back to commit-msg file (pre-commit)
           ▼
       Exit code 0/1
```

### Module responsibilities

```
commit_check/
├── __init__.py          # Package constants: DEFAULT_COMMIT_TYPES, DEFAULT_BRANCH_TYPES, DEFAULT_BOOLEAN_RULES
├── main.py              # CLI entry point, argument parsing, StdinReader, --fix flow
├── config.py            # TOML file loading (uses tomllib on Python 3.11+, tomli on older)
├── config_merger.py     # ConfigMerger: merges CLI → Env → TOML → Defaults
├── rule_builder.py      # RuleBuilder: creates ValidationRule objects from config + catalog
├── rules_catalog.py     # Catalog of all rules (COMMIT_RULES, BRANCH_RULES)
├── engine.py            # ValidationEngine, BaseValidator ABC, ValidationContext, ValidationResult, CheckResult
├── fixer.py             # CommitFixer: rule-driven commit message auto-repair (--fix / --yes)
├── imperatives.py       # ~258 English imperative verbs for subject validation
└── util.py              # Git operations, output formatting (_print_failure)
```

### Validator class hierarchy

```
BaseValidator (ABC)
├── CommitMessageValidator        # Full message: conventional commits format
├── SubjectValidator (ABC)
│   ├── SubjectCapitalizationValidator  # First letter must be uppercase
│   ├── SubjectImperativeValidator      # Subject must start with imperative verb
│   └── SubjectLengthValidator          # Subject length min/max
├── AuthorValidator               # Author name and email format
├── BranchValidator               # Branch naming conventions
├── MergeBaseValidator            # Merge base / rebase target
├── SignoffValidator              # Signed-off-by trailer presence
├── BodyValidator                 # Commit body presence
└── CommitTypeValidator           # Handles merge/revert/fixup/wip/empty commits

CommitFixer (standalone, in fixer.py)
└── fix(message, failed_checks) → FixResult
    ├── _fix_wip()            # Strip "WIP:" prefix
    ├── _fix_imperative()     # Convert past/present tense to imperative
    ├── _fix_capitalized()    # Capitalize description after conventional prefix
    └── _fix_signoff()        # Append Signed-off-by from git config
```

### Configuration priority cascade

| Priority | Source | Example |
|----------|--------|---------|
| 1 (highest) | CLI arguments | `--subject-max-length=72` |
| 2 | Environment variables | `CCHK_SUBJECT_MAX_LENGTH=72` |
| 3 | TOML config files | `cchk.toml`, `.github/cchk.toml`, etc. |
| 4 (lowest) | Built-in defaults | defined in `commit_check/__init__.py` |

## Development setup

### Prerequisites

- Python 3.9 or newer
- `nox` for running build sessions: `pip install nox`

### Install in development mode

```bash
git clone https://github.com/commit-check/commit-check.git
cd commit-check
pip install -e ".[test]"
```

### Run tests

```bash
# Fastest: run pytest directly
pytest tests/ -v

# With coverage report
nox -s coverage
```

### Lint and format

```bash
# Run all pre-commit hooks (ruff, mypy, codespell, etc.)
nox -s lint

# Or install hooks for automatic checks on every commit
pre-commit install
```

### Build documentation

```bash
# One-time build
nox -s docs

# Live preview with auto-reload
nox -s docs-live
```

### Test the pre-commit hook locally

```bash
pre-commit try-repo  ./../commit-check/ check-message --verbose --hook-stage commit-msg --commit-msg-filename .git/COMMIT_EDITMSG
```

### Debug commit-check wheel package

```bash
python3 -m pip install --upgrade pip
pip install -e ./../commit-check/
commit-check -m
```

## Test commit-check pre-commit hook on GitHub

```yaml
-   repo: https://github.com/commit-check/commit-check
    rev: the tag or revision # update it to test commit hash
    hooks:
    -   id: check-message
    -   id: check-branch
    -   id: check-author-email
```

We appreciate your contributions to make Commit Check even better!
