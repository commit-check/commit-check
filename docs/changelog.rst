Changelog
=========

All **notable changes** to this project will be documented in this file.

Full changelog available at `GitHub releases <https://github.com/commit-check/commit-check/releases>`_.

v2.11.0 (2026-07-06)
-------------------

New Features
~~~~~~~~~~~~

* **AI attribution governance** — Added support for forbidding known AI tool
  signatures (e.g., ``Co-authored-by: Copilot``) in commit messages. New
  ``[commit]`` config option ``forbid_ai_attribution`` (boolean, default
  ``false``) rejects commits co-authored by AI coding agents. See PR :pr:`456`.

Bug Fixes
~~~~~~~~~

* Fixed ``MergeBaseValidator`` branch detection — replaced ``git branch -a``
  regex matching with ``git rev-parse --verify`` to avoid false positives
  (e.g., pattern ``main`` matching ``main-staging``). See PR :pr:`451`.

Chores
~~~~~~

* Added OpenSSF Scorecard workflow, badge, and pinned dependency SHAs for CI
* Migrated PyPI publishing to ``pypa/gh-action-pypi-publish``
* Removed OpenSSF Scorecard badge after evaluation (moved to Scorecard dashboard)


v2.10.1 (2026-06-30)
-------------------

Bug Fixes
~~~~~~~~~

* **WIP detection case-insensitivity** — ``WIP`` (``[WIP]``, ``WIP:``, ``wip:``,
  etc.) is now recognized regardless of case across all common patterns.
  See PR :pr:`448`.
* **Conventional commit special characters** — Allowed special characters
  (parentheses, brackets, etc.) in the description part of conventional commit
  messages. See PR :pr:`447`.

Refactors
~~~~~~~~~

* Extracted ``_get_commit_message`` to ``BaseValidator`` to remove code
  duplication across validators. See PR :pr:`445`.
* Removed legacy YAML config parsing code from ``util.py``.
  See PR :pr:`444`.


v2.10.0 (2026-06-26)
-------------------

New Features
~~~~~~~~~~~~

* **Dependabot / Renovate as default branch type** — ``dependabot/`` and
  ``renovate/`` branch prefixes are now included in ``DEFAULT_BRANCH_TYPES``,
  so dependency update branches are automatically recognized.
  See PR :pr:`442`.


v2.9.0 (2026-06-22)
-------------------

New Features
~~~~~~~~~~~~

* **AI agent branch prefixes (Conventional Branch v1.1.0)** — Added
  ``ai/``, ``claude/``, ``codex/``, ``copilot/``, and ``cursor/`` to
  ``DEFAULT_BRANCH_TYPES`` so branches created by AI coding agents are
  recognized as valid. See PR :pr:`438`.


v2.8.1 (2026-06-22)
-------------------

Chores
~~~~~~

* Fixed 27 SonarQube code-quality issues across source and test files,
  including path traversal vulnerability fix, cognitive complexity
  reduction, and duplicate branch consolidation. See PR :pr:`436`.
* Added SchemaStore IDE autocompletion support for ``cchk.toml``.
  See PR :pr:`433`.


v2.8.0 (2026-06-13)
-------------------

New Features
~~~~~~~~~~~~

* **Custom commit message pattern** — New ``message_pattern`` option in the
  ``[commit]`` config section allows replacing the built-in Conventional Commits
  regex with a user-defined regex pattern. Also supported via the
  ``CCHK_MESSAGE_PATTERN`` environment variable. See PR :pr:`427`.

Breaking Changes
~~~~~~~~~~~~~~~~

* **Dropped Python 3.9 support** — Minimum required Python version is now
  3.10. Type annotations have been modernized (PEP 604/585) and the
  ``py.typed`` marker added for downstream type checkers.
  See PR :pr:`424`.


v2.7.1 (2026-06-08)
-------------------

Chores
~~~~~~

* Added ``auto`` to the list of imperative verbs. See PR :pr:`417`.
* Added commit-check vs GitHub Rulesets comparison table to the README.
  See PR :pr:`419`.


v2.7.0 (2026-05-16)
-------------------

New Features
~~~~~~~~~~~~

* **Force push detection and blocking** — Added ``--no-force-push`` CLI flag and
  ``check-no-force-push`` pre-push hook that inspect pushed ref ancestry via
  ``git merge-base --is-ancestor`` to detect and block ``git push --force`` and
  ``git push -f``. A new ``[push]`` TOML config section with
  ``allow_force_push`` (default ``true``) controls the behavior. Environment
  variable ``CCHK_ALLOW_FORCE_PUSH`` is also supported.

* **``validate_push()`` API** — New ``commit_check.api.validate_push()``
  function for programmatic push safety checks, matching the ``--no-force-push``
  CLI behavior without spawning a subprocess.

* **Standalone mode** — When ``--no-force-push`` is run outside a pre-push hook
  (no stdin), it checks whether pushing ``HEAD`` to its configured upstream
  would require force, using ``git ls-remote`` and optional ``git fetch`` to
  resolve the remote commit.

* **Expanded imperative verbs** — Added 156 new imperative verbs across 10
  categories (auth/security, data ops, lifecycle, I/O, debugging, UI/UX,
  engineering, general), growing the total from 234 to 390.
  See PR :pr:`414`.


v2.6.0 (2026-04-20)
-------------------

New Features
~~~~~~~~~~~~

* **Lower-noise CLI failure output** — Added ``--no-banner`` to suppress the ASCII art header while preserving detailed errors and suggestions.
* **Compact failure mode** — Added ``--compact`` to print one ``[FAIL]`` line per failing check for CI logs and automation-friendly terminal output. This mode also suppresses the banner.

Bug Fixes
~~~~~~~~~

* Fixed ``print_error_header`` state handling so repeated validations stay consistent when ``--compact`` is used.

v2.5.0 (2026-04-03)
-------------------

New Features
~~~~~~~~~~~~

* **Co-author bypass in ``ignore_authors``** — ``_should_skip_commit_validation()`` now parses ``Co-authored-by:`` trailers in the commit message body. If any co-author name matches ``ignore_authors``, all commit checks are skipped. Useful for AI bots that co-author commits (e.g., ``coderabbitai[bot]``).
* **Organization-level config inheritance via ``inherit_from``** — New top-level TOML key that loads a parent config from a GitHub shorthand (``github:owner/repo:path``), a local file path, or an HTTPS URL, then deep-merges it with local settings. HTTP (non-TLS) URLs are rejected to prevent MITM attacks.
* **Git config author validation** — ``AuthorValidator`` now checks ``git config user.name`` / ``user.email`` first (the identity used for the *next* commit), falling back to ``git log`` if unset. Previously, a misconfigured identity would pass if the last commit had a valid author.

Bug Fixes
~~~~~~~~~

* Fixed incorrect mock target in ``test_main_with_message_empty_string_no_stdin_with_git``: was patching ``commit_check.util.get_commit_info`` (ineffective) instead of ``commit_check.engine.get_commit_info``.

v2.0.0 (2025-10-01)
-------------------

.. Attention::
    This major release introduces significant architectural changes and breaking updates to commit-check. Please review carefully before upgrading.

What's New
~~~~~~~~~~

* **TOML Configuration** — Replaces the old ``.commit-check.yml`` with ``cchk.toml`` or ``commit-check.toml`` for clearer syntax.
* **Simplified CLI & Hooks** — Legacy pre-commit hooks and command-line options have been removed for a cleaner, more consistent interface.
* **New Validation Engine** — The validation system has been completely redesigned around a new ValidationEngine to improve maintainability and flexibility.

Breaking Changes
^^^^^^^^^^^^^^^^

Configuration Format:

* ``.commit-check.yml`` has been replaced with ``cchk.toml`` or ``commit-check.toml``.
* All YAML configurations must be migrated to TOML from this version onward.
* See the `Migration Guide <migration.html>`_ for step-by-step instructions.

Removed Pre-commit Hooks and CLI Options:

* Several legacy hooks and command-line flags have been removed in favor of a simplified interface.
* Removed hooks: ``check-commit-signoff``, ``check-merge-base``, ``check-imperative``.
* Removed CLI options: ``--signoff``, ``--merge-base``, ``--imperative``.

Module Removal:

* The following legacy modules have been removed: ``author.py``, ``branch.py``, ``commit.py``, ``error.py``.

Architecture Redesign:

* The validation system has been completely restructured around the new ``ValidationEngine``, breaking compatibility with any code or integrations relying on the old module structure.

See PR :pr:`280`

v0.10.2 (2025-08-26)
--------------------

Last release before the big v2.0 changes.

v0.1.0 (2022-11-02)
--------------------

Initial release of commit-check.
