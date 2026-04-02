Commit Check
============

.. |pypi-version| image:: https://img.shields.io/pypi/v/commit-check?logo=python&logoColor=white&color=%232c9ccd
    :target: https://pypi.org/project/commit-check/
    :alt: PyPI

.. |ci-badge| image:: https://github.com/commit-check/commit-check/actions/workflows/main.yml/badge.svg
    :target: https://github.com/commit-check/commit-check/actions/workflows/main.yml
    :alt: CI

.. |sonar-badge| image:: https://sonarcloud.io/api/project_badges/measure?project=commit-check_commit-check&metric=alert_status
    :target: https://sonarcloud.io/summary/new_code?id=commit-check_commit-check
    :alt: Quality Gate Status

.. |codecov-badge| image:: https://codecov.io/gh/commit-check/commit-check/branch/main/graph/badge.svg?token=GC2U5V5ZRT
    :target: https://codecov.io/gh/commit-check/commit-check
    :alt: CodeCov

.. |commit-check-badge| image:: https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white&color=%232c9ccd
    :target: https://github.com/commit-check/commit-check
    :alt: commit-check

.. |slsa-badge| image:: https://slsa.dev/images/gh-badge-level3.svg
    :target: https://slsa.dev
    :alt: SLSA

.. |pypi-downloads| image:: https://img.shields.io/pypi/dm/commit-check?color=%232c9ccd
    :target: https://pypi.org/project/commit-check/
    :alt: PyPI Downloads

.. |python-versions| image:: https://img.shields.io/pypi/pyversions/commit-check?logo=python&logoColor=white
    :target: https://pypi.org/project/commit-check/
    :alt: Python Versions

|ci-badge| |sonar-badge| |pypi-version| |pypi-downloads| |python-versions| |commit-check-badge| |codecov-badge| |slsa-badge|

Overview
--------

**Commit Check** (aka **cchk**) is the most comprehensive open-source tool for enforcing Git commit standards — including commit messages, branch naming, author identity, commit signoff, and more — helping teams maintain consistency and compliance across every repository.

As a lightweight, free alternative to GitHub Enterprise `Metadata restrictions <https://docs.github.com/en/enterprise-server@3.11/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#metadata-restrictions>`_
and Bitbucket's paid `Yet Another Commit Checker <https://marketplace.atlassian.com/apps/1211854/yet-another-commit-checker?tab=overview&hosting=datacenter>`_ plugin, Commit Check integrates DevOps principles and Infrastructure as Code (IaC) practices for a modern workflow.

**Why Commit Check?**

.. list-table::
   :header-rows: 1
   :widths: 40 20 20 20

   * - Feature
     - Commit Check ✅
     - commitlint
     - pre-commit hooks
   * - Conventional Commits enforcement
     - ✅
     - ✅
     - ✅
   * - Branch naming validation
     - ✅
     - ❌
     - Partial
   * - Author name / email validation
     - ✅
     - ❌
     - ❌
   * - Signoff / DCO check
     - ✅
     - ❌
     - ❌
   * - Co-author ignore list
     - ✅
     - ❌
     - ❌
   * - Organization-level config inheritance
     - ✅
     - ❌
     - ❌
   * - Zero-config defaults
     - ✅
     - ❌
     - ❌
   * - Works without Node.js
     - ✅
     - ❌
     - ✅
   * - TOML configuration
     - ✅
     - ❌
     - ✅
   * - pre-commit framework integration
     - ✅
     - ✅
     - ✅
   * - CI/CD environment variables
     - ✅
     - Partial
     - ❌
   * - SLSA Level 3 supply chain security
     - ✅
     - ❌
     - ❌

What's New in v2.0.0
--------------------

Version 2.0.0 is a major release featuring a new configuration format, a modernized architecture, and an improved user experience.

**✨ Highlights**

* **TOML Configuration** — Replaces ``.commit-check.yml`` with ``cchk.toml`` or ``commit-check.toml`` for clearer, more consistent syntax.
* **Simplified CLI & Hooks** — Legacy pre-commit hooks and options removed to deliver a cleaner, more streamlined interface.
* **New Validation Engine** — Fully redesigned for greater flexibility, performance, and maintainability.
* **Co-author ignore support** — Bypass checks when a commit is co-authored by a bot or trusted identity in ``ignore_authors``.
* **Organization-level configuration** — Use ``inherit_from`` to share a base config across all repositories in your org.
* **Git config author validation** — ``--author-name`` and ``--author-email`` now validate the configured identity for the next commit.

For the full list of updates and improvements, visit the `What's New <https://commit-check.github.io/commit-check/what-is-new.html>`_ page.

Installation
------------

To install Commit Check, you can use pip:

.. code-block:: bash

    pip install commit-check

Or install directly from the GitHub repository:

.. code-block:: bash

    pip install git+https://github.com/commit-check/commit-check.git@main

Then, run ``commit-check --help`` or ``cchk --help`` (alias for ``commit-check``) from the command line.
For more information, see the `docs <https://commit-check.github.io/commit-check/cli_args.html>`_.


Quick Start
-----------

**1. Install and run with zero configuration:**

.. code-block:: bash

    pip install commit-check
    commit-check --message --branch

**2. Add to your pre-commit hooks** (``.pre-commit-config.yaml``):

.. code-block:: yaml

    repos:
      - repo: https://github.com/commit-check/commit-check
        rev: v2.3.0
        hooks:
          - id: check-message
          - id: check-branch

**3. Add a badge to your repository:**

.. code-block:: text

    [![commit-check](https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white&color=%232c9ccd)](https://github.com/commit-check/commit-check)


Configuration
-------------

Commit Check can be configured in three ways (in order of priority):

1. **Command-line arguments** — Override settings for specific runs
2. **Environment variables** — Configure via ``CCHK_*`` environment variables
3. **Configuration files** — Use ``cchk.toml`` or ``commit-check.toml``

Use Default Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

- **Commit Check** uses a `default configuration <https://github.com/commit-check/commit-check/blob/main/docs/configuration.rst>`_ if you do not provide a ``cchk.toml`` or ``commit-check.toml`` file.

- The default configuration is lenient — it only checks whether commit messages follow the `Conventional Commits <https://www.conventionalcommits.org/en/v1.0.0/#summary>`_ specification and branch names follow the `Conventional Branch <https://conventional-branch.github.io/#summary>`_ convention.

Use Custom Configuration File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To customize the behavior, create a configuration file named ``cchk.toml`` or ``commit-check.toml`` in your repository's root directory or in the ``.github`` folder, e.g., `cchk.toml <https://github.com/commit-check/commit-check/blob/main/cchk.toml>`_ or ``.github/cchk.toml``.

.. code-block:: toml

    [commit]
    # https://www.conventionalcommits.org
    conventional_commits = true
    subject_imperative = true
    subject_max_length = 80
    allow_commit_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore", "ci"]
    allow_merge_commits = true
    allow_wip_commits = false
    require_signed_off_by = false
    # Bypass checks for bot/automation authors and co-authors:
    ignore_authors = ["dependabot[bot]", "renovate[bot]", "copilot[bot]"]

    [branch]
    # https://conventional-branch.github.io/
    conventional_branch = true
    allow_branch_types = ["feature", "bugfix", "hotfix", "release", "chore", "feat", "fix"]

Organization-Level Configuration (inherit_from)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Share a base configuration across all repositories in your organization using ``inherit_from``:

.. code-block:: toml

    # .github/cchk.toml — inherits from org-level config, then overrides locally
    inherit_from = "github:my-org/.github:cchk.toml"

    [commit]
    subject_max_length = 72  # Local override

The ``inherit_from`` field accepts:

* A **GitHub shorthand** (recommended): ``inherit_from = "github:owner/repo:path/to/cchk.toml"``
* A **GitHub shorthand with ref**: ``inherit_from = "github:owner/repo@main:path/to/cchk.toml"``
* A **local file path** (relative or absolute): ``inherit_from = "../shared/cchk.toml"``
* An **HTTPS URL**: ``inherit_from = "https://example.com/cchk.toml"``

The ``github:`` shorthand fetches from ``raw.githubusercontent.com``. HTTP (non-TLS) URLs are rejected for security.

Local settings always **override** the inherited base configuration.

Use CLI Arguments or Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For one-off checks or CI/CD pipelines, you can configure via CLI arguments or environment variables:

.. code-block:: bash

    # Using CLI arguments
    commit-check --message --subject-imperative=true --subject-max-length=72

    # Using environment variables
    export CCHK_SUBJECT_IMPERATIVE=true
    export CCHK_SUBJECT_MAX_LENGTH=72
    commit-check --message

    # In pre-commit hooks (.pre-commit-config.yaml)
    repos:
      - repo: https://github.com/commit-check/commit-check
        rev: v2.3.0
        hooks:
          - id: check-message
            args:
              - --subject-imperative=false
              - --subject-max-length=100

See the `Configuration documentation <https://commit-check.github.io/commit-check/configuration.html>`_ for all available options.

Usage
-----

For detailed usage instructions including pre-commit hooks, CLI commands, and STDIN examples, see the `Usage Examples documentation <https://commit-check.github.io/commit-check/example.html>`_.

Examples
--------

.. image:: https://github.com/commit-check/commit-check/raw/main/docs/demo.gif
    :alt: commit-check demo
    :align: center

|

Check Commit Message Failed

.. code-block:: text

    Commit rejected by Commit-Check.

      (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)
       / ._. \      / ._. \      / ._. \      / ._. \      / ._. \
     __\( C )/__  __\( H )/__  __\( E )/__  __\( C )/__  __\( K )/__
    (_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)
       || E ||      || R ||      || R ||      || O ||      || R ||
     _.' '-' '._  _.' '-' '._  _.' '-' '._  _.' '-' '._  _.' '-' '._
    (.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)
     `-´     `-´  `-´     `-´  `-´     `-´  `-´     `-´  `-´     `-´

    Commit rejected.

    Type message check failed ==> test commit message check
    The commit message should follow Conventional Commits. See https://www.conventionalcommits.org
    Suggest: Use <type>(<scope>): <description>, where <type> is one of: feat, fix, docs, style, refactor, test, chore, ci


Check Branch Naming Failed

.. code-block:: text

    Commit rejected by Commit-Check.

      (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)
       / ._. \      / ._. \      / ._. \      / ._. \      / ._. \
     __\( C )/__  __\( H )/__  __\( E )/__  __\( C )/__  __\( K )/__
    (_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)
       || E ||      || R ||      || O ||      || R ||      || R ||
     _.' '-' '._  _.' '-' '._  _.' '-' '._  _.' '-' '._  _.' '-' '._
    (.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)(.-./`-´\.-.)
     `-´     `-´  `-´     `-´  `-´     `-´  `-´     `-´  `-´     `-´

    Commit rejected.

    Type branch check failed ==> test-branch
    The branch should follow Conventional Branch. See https://conventional-branch.github.io/
    Suggest: Use <type>/<description> with allowed types or add branch name to allow_branch_names in config, or use ignore_authors in config branch section to bypass

More examples see `example documentation <https://commit-check.github.io/commit-check/example.html>`_.

Badging your repository
-----------------------

You can add a badge to your repository to show that you use commit-check!

.. image:: https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white&color=%232c9ccd
    :target: https://github.com/commit-check/commit-check
    :alt: commit-check

Markdown

.. code-block:: text

    [![commit-check](https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white&color=%232c9ccd)](https://github.com/commit-check/commit-check)

reStructuredText

.. code-block:: text

    .. image:: https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white&color=%232c9ccd
        :target: https://github.com/commit-check/commit-check
        :alt: commit-check


Versioning
----------

Versioning follows `Semantic Versioning <https://semver.org/>`_.

Have question or feedback?
--------------------------

Please post to `issues <https://github.com/commit-check/commit-check/issues>`_ for feedback, feature requests, or bug reports.

License
-------

This project is released under the `MIT License <https://github.com/commit-check/commit-check/blob/main/LICENSE>`_
