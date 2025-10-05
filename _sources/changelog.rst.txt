:status: new

Changelog
=========

All **notable changes** to this project will be documented in this file.

Full changelog available at `GitHub releases <https://github.com/commit-check/commit-check/releases>`_.

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
