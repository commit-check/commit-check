# Commit Check Development Instructions

Commit Check is a Python CLI tool and pre-commit hook that validates commit messages, branch naming, author information, and more according to Conventional Commits and Conventional Branch conventions.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Prerequisites and Setup
```bash
# Install Python dependencies (required)
python3 -m pip install --upgrade pip
python3 -m pip install nox

# Install package in development mode with PYTHONPATH (network timeout workaround)
export PYTHONPATH=/home/runner/work/commit-check/commit-check
python3 -m pip install pyyaml  # Core dependency
```

### Build and Package
```bash
# Build wheel package -- NETWORK ISSUES: Often fails due to PyPI timeouts in CI environments
# Takes ~10 seconds when working, ~20+ seconds when timing out
nox -s build

# Manual build workaround when nox fails:
python3 -m pip wheel --no-deps -w dist .  # NETWORK ISSUES: Also fails due to build dependencies

# Install wheel (depends on build)
nox -s install-wheel  # NETWORK ISSUES: Often fails due to PyPI timeouts in CI environments
```

### Testing
```bash
# Run tests directly (fastest, most reliable) -- takes ~1 second. Set timeout to 30+ seconds.
PYTHONPATH=/home/runner/work/commit-check/commit-check python3 -m pytest tests/ -v

# Alternative: Run tests via nox (may timeout due to network)
nox -s coverage  # NETWORK ISSUES: Often fails due to PyPI timeouts, takes 5+ minutes when working
```

### Linting and Code Quality
```bash
# NETWORK ISSUES: nox -s lint often fails due to pre-commit installation timeouts
# Manual workaround for linting:
python3 -m pip install pre-commit  # May timeout, retry if needed
pre-commit install --hook-type pre-commit
pre-commit run --all-files --show-diff-on-failure  # Takes 2-5 minutes for full run
```

### Documentation
```bash
# NETWORK ISSUES: Documentation builds fail due to external dependencies (fonts.google.com)
# Install docs dependencies (may timeout)
python3 -m pip install sphinx-immaterial sphinx-autobuild

# Build docs -- FAILS due to network restrictions in CI environments
PYTHONPATH=/home/runner/work/commit-check/commit-check sphinx-build -E -W -b html docs _build/html
```

## Validation Scenarios

### Manual Testing (Essential after changes)
Always manually validate functionality with these scenarios:

```bash
# Set PYTHONPATH for direct module execution
export PYTHONPATH=/home/runner/work/commit-check/commit-check

# Test 1: Valid conventional commit message
echo "fix: correct issue with validation" > test_commit.txt
python3 -m commit_check.main --message test_commit.txt
# Expected: Exit code 0 (success)

# Test 2: Invalid commit message format
echo "invalid commit message" > test_commit_invalid.txt
python3 -m commit_check.main --message test_commit_invalid.txt
# Expected: Exit code 1, shows ASCII art rejection and error details

# Test 3: Complex conventional commit with scope and body
echo "feat(api): add new user endpoint

This adds support for creating new users via the REST API.

Breaking Change: API version updated to v2" > test_complex_commit.txt
python3 -m commit_check.main --message test_complex_commit.txt
# Expected: Exit code 0 (success)

# Test 4: Branch name validation
python3 -m commit_check.main --branch
# Expected: Depends on current branch name, should show validation result

# Test 5: Help and version
python3 -m commit_check.main --help
python3 -m commit_check.main --version

# Test 6: Configuration validation
python3 -m commit_check.main --config .commit-check.yml --dry-run

# Test 7: Multiple checks at once
python3 -m commit_check.main --message test_commit.txt --branch --dry-run

# Clean up test files
rm -f test_commit.txt test_commit_invalid.txt test_complex_commit.txt
```

### Integration Testing
```bash
# Test as pre-commit hook
pre-commit try-repo . --verbose --hook-stage prepare-commit-msg

# Test wheel installation
python3 -m pip install dist/*.whl  # After running nox -s build
commit-check --help  # Verify CLI works
cchk --help  # Verify alias works
```

## Known Issues and Workarounds

### Network Connectivity
- **Issue**: PyPI timeouts during pip install in CI environments
- **Workaround**: Use `--timeout=10` flag, install dependencies individually, or use PYTHONPATH for development

### Build System
- **Issue**: nox sessions fail due to dependency installation timeouts
- **Workaround**: Run commands directly with PYTHONPATH instead of nox sessions

### Documentation
- **Issue**: Sphinx build fails due to external font loading (fonts.google.com)
- **Status**: Cannot be fixed in restricted CI environments

## Configuration and Important Files

### Repository Structure
```
.
├── commit_check/           # Main Python package
│   ├── __init__.py        # Package configuration and defaults
│   ├── main.py           # CLI entry point
│   ├── commit.py         # Commit message validation
│   ├── branch.py         # Branch name validation
│   ├── author.py         # Author validation
│   └── util.py           # Utility functions
├── tests/                 # Test suite (108 tests)
├── docs/                  # Sphinx documentation
├── .commit-check.yml      # Default configuration
├── pyproject.toml        # Package metadata and build config
├── noxfile.py           # Build automation
└── .pre-commit-config.yaml # Pre-commit configuration
```

### Key Files
- **pyproject.toml**: Package configuration, dependencies, entry points
- **noxfile.py**: Automated build tasks (lint, test, build, docs)
- **.commit-check.yml**: Default validation rules for the tool itself
- **commit_check/__init__.py**: Default configuration templates and constants

## Common Commands Summary

| Command | Purpose | Timing | Notes |
|---------|---------|---------|-------|
| `nox -s build` | Build wheel | ~10s | Reliable |
| `pytest tests/` | Run tests | ~1s | Fastest, most reliable |
| `nox -s coverage` | Tests + coverage | 5+ min | Often times out |
| `nox -s lint` | Code quality | 2-5 min | Often times out |
| `python3 -m commit_check.main --help` | CLI help | Instant | Always works |

## Tool Behavior and Features

### Commit Message Validation
- **Conventional Commits**: Enforces standard format: `type(scope): description`
- **Supported types**: build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test
- **Scope**: Optional, e.g., `feat(api): add endpoint`
- **Breaking changes**: Supports `!` notation: `feat!: breaking change`
- **Merge commits**: Special handling for merge commit messages

### Branch Name Validation
- **Conventional Branches**: Enforces patterns like `feature/`, `bugfix/`, etc.
- **Allowed prefixes**: bugfix/, feature/, release/, hotfix/, task/, chore/
- **Special branches**: master, main, HEAD, PR-* are allowed

### Author Validation
- **Author name**: Checks for valid name format
- **Author email**: Validates email format
- **Commit signoff**: Checks for "Signed-off-by:" trailer

### Exit Codes
- **0**: All checks passed
- **1**: One or more checks failed
- **Error output**: Colorized ASCII art rejection message with specific error details

## When to Use What

### For Quick Development and Testing
- **Use**: Direct Python module execution with PYTHONPATH
- **Commands**: `PYTHONPATH=/home/runner/work/commit-check/commit-check python3 -m commit_check.main`
- **Best for**: Testing changes, debugging, manual validation

### For Production Builds (when network works)
- **Use**: nox sessions for full build pipeline
- **Commands**: `nox -s build`, `nox -s coverage`, `nox -s lint`
- **Best for**: CI/CD, release preparation, comprehensive testing

### For Isolated Testing
- **Use**: Direct pytest execution
- **Commands**: `PYTHONPATH=/home/runner/work/commit-check/commit-check python3 -m pytest tests/`
- **Best for**: Unit testing, TDD, debugging test failures

### For Pre-commit Integration
- **Use**: pre-commit commands
- **Commands**: `pre-commit try-repo .`, `pre-commit run --all-files`
- **Best for**: Validating hook behavior, testing integration

## Development Workflow
1. **Always** set `export PYTHONPATH=/home/runner/work/commit-check/commit-check`
2. **Always** test CLI functionality manually after changes using validation scenarios above
3. **Always** run `pytest tests/` before committing changes
4. **Always** verify build works with `nox -s build`
5. Avoid relying on nox for dependency installation in CI environments
