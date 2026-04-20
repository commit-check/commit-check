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

.. |pypi-downloads| image:: https://img.shields.io/pypi/dm/commit-check?color=%232c9ccd
    :target: https://pypi.org/project/commit-check/
    :alt: PyPI Downloads

.. |python-versions| image:: https://img.shields.io/pypi/pyversions/commit-check?logo=python&logoColor=white
    :target: https://pypi.org/project/commit-check/
    :alt: Python Versions

|ci-badge| |sonar-badge| |pypi-version| |pypi-downloads| |python-versions| |commit-check-badge| |codecov-badge|

.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none

Overview
--------

**Commit Check** (aka **cchk**) is the most comprehensive open-source tool for enforcing Git commit standards — including commit messages, branch naming, author identity, commit signoff, and more — helping teams maintain consistency and compliance across every repository.

As a lightweight, free alternative to GitHub Enterprise `Metadata restrictions <https://docs.github.com/en/enterprise-server@3.11/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#metadata-restrictions>`_
and Bitbucket's paid `Yet Another Commit Checker <https://marketplace.atlassian.com/apps/1211854/yet-another-commit-checker?tab=overview&hosting=datacenter>`_ plugin, Commit Check integrates DevOps principles and Infrastructure as Code (IaC) practices for a modern workflow.

.. image:: https://github.com/commit-check/commit-check/raw/main/docs/demo.gif
    :alt: commit-check demo
    :align: center

|

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
        rev: v2.6.0
        hooks:
          - id: check-message
          - id: check-branch

**3. Add a badge to your repository:**

.. code-block:: text

    [![commit-check](https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white&color=%232c9ccd)](https://github.com/commit-check/commit-check)

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
        rev: v2.6.0
        hooks:
          - id: check-message
            args:
              - --subject-imperative=false
              - --subject-max-length=100

See the `Configuration documentation <https://commit-check.github.io/commit-check/configuration.html>`_ for all available options.

AI-Native Usage
---------------

Commit Check is designed to be consumed by AI agents, LLM toolchains, and
automation scripts — not just by humans reading terminal output.

Machine-Readable JSON Output (``--format json``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass ``--format json`` to any CLI invocation to receive structured JSON instead
of human-readable ASCII art.  The exit code is unchanged (``0`` = pass, ``1`` = fail),
so existing CI scripts continue to work:

.. code-block:: bash

    echo "feat: add streaming support" | commit-check -m --format json

.. code-block:: json

    {
      "status": "pass",
      "checks": [
        { "check": "message",           "status": "pass", "value": "", "error": "", "suggest": "" },
        { "check": "subject_imperative", "status": "pass", "value": "", "error": "", "suggest": "" }
      ]
    }

On failure the failing checks carry the full ``error`` and ``suggest`` fields
an agent needs to self-correct:

.. code-block:: bash

    echo "wip bad commit" | commit-check -m --format json

.. code-block:: json

    {
      "status": "fail",
      "checks": [
        {
          "check":   "message",
          "status":  "fail",
          "value":   "wip bad commit",
          "error":   "The commit message should follow Conventional Commits. See https://www.conventionalcommits.org",
          "suggest": "Use <type>(<scope>): <description>, where <type> is one of: feat, fix, docs, ..."
        }
      ]
    }

Quieter Human-Readable Output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For terminal workflows that still want plain text, commit-check now supports
two lower-noise output modes:

* ``--no-banner`` keeps the normal failure details and suggestions, but removes
  the ASCII-art failure banner.
* ``--compact`` emits a single ``[FAIL]`` line per failing check and implies
  ``--no-banner``.

.. code-block:: bash

    echo "wip bad commit" | commit-check -m --no-banner

.. code-block:: text

    Type message check failed ==> wip bad commit
    It doesn't match regex: ^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)|(Merge).*|(fixup!.*)
    The commit message should follow Conventional Commits. See https://www.conventionalcommits.org
    Suggest: Use <type>(<scope>): <description>, where <type> is one of: feat, fix, docs, ...

.. code-block:: bash

    echo "wip bad commit" | commit-check -m --compact

.. code-block:: text

    [FAIL] message: wip bad commit

Python API (no subprocess required)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``commit_check.api`` module exposes a lightweight, import-friendly interface
so AI agents, tools, and scripts can validate commits **without spawning a
subprocess**.  All functions return plain dicts that are easy to serialise,
forward to an LLM, or chain into larger workflows:

.. code-block:: python

    from commit_check.api import validate_message, validate_branch, validate_all

    # --- validate a single commit message ---
    result = validate_message("feat: add streaming support")
    print(result["status"])          # "pass"

    # --- validate a branch name ---
    result = validate_branch("feature/add-streaming")
    print(result["status"])          # "pass"

    # --- run multiple checks at once ---
    result = validate_all(
        message="feat: implement new feature",
        branch="feature/new-feature",
        author_name="Ada Lovelace",
        author_email="ada@example.com",
    )
    if result["status"] == "fail":
        for check in result["checks"]:
            if check["status"] == "fail":
                print(f"[{check['check']}] {check['error']}")
                print(f"  suggestion: {check['suggest']}")

    # --- supply a custom config to restrict allowed types ---
    result = validate_message(
        "docs: update readme",
        config={"commit": {"allow_commit_types": ["feat", "fix"]}},
    )
    print(result["status"])          # "fail" — 'docs' not in allowed types

**Return-value schema** (all API functions):

.. code-block:: python

    {
        "status": "pass" | "fail",
        "checks": [
            {
                "check":   "<rule name>",
                "status":  "pass" | "fail",
                "value":   "<actual value that was checked>",
                "error":   "<human-readable error description>",
                "suggest": "<how to fix>",
            },
            # ... one entry per active rule
        ]
    }

Available API functions:

* ``validate_message(message, *, config=None)`` — validate a commit message string
* ``validate_branch(branch=None, *, config=None)`` — validate a branch name (defaults to current git branch)
* ``validate_author(name=None, email=None, *, config=None)`` — validate author name/email
* ``validate_all(message, branch, author_name, author_email, *, config=None)`` — run all checks at once

For detailed usage instructions including pre-commit hooks, CLI commands, and STDIN examples, see the `Usage Examples documentation <https://commit-check.github.io/commit-check/example.html>`_.

Examples
--------

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
       || E ||      || R ||      || R ||      || O ||      || R ||
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


Why Commit Check?
-----------------

The table below compares common approaches to commit policy enforcement.
``commitlint`` is a specialized commit-message linter. Custom Git hooks and
the ``pre-commit`` framework are integration mechanisms, so the last column
reflects a DIY approach rather than built-in product features.

.. list-table::
   :header-rows: 1
   :widths: 36 18 18 28

   * - Feature
     - Commit Check ✅
     - commitlint
     - Custom hooks
   * - Conventional Commits enforcement
     - ✅
     - ✅
     - DIY
   * - Branch naming validation
     - ✅
     - ❌
     - DIY
   * - Author name / email validation
     - ✅
     - ❌
     - DIY
   * - Signed-off-by trailer enforcement
     - ✅
     - ✅
     - DIY
   * - Co-author ignore list
     - ✅
     - ❌
     - DIY
   * - Organization-level shared config
     - ✅
     - ✅
     - DIY
   * - Zero-config defaults
     - ✅
     - ❌
     - ❌
   * - Works without Node.js
     - ✅
     - ❌
     - Depends
   * - Native TOML configuration
     - ✅
     - ❌
     - Depends
   * - Git hook / pre-commit integration
     - ✅
     - Partial
     - ✅
   * - CI/CD-friendly configuration
     - ✅
     - Partial
     - DIY

For ``commitlint``, organization-level shared config is typically delivered via
shareable config packages or local files. ``DIY`` means you can implement a
capability with custom Git hooks or ``pre-commit`` scripts, but it is not
provided as a turnkey policy layer.


Versioning
----------

Versioning follows `Semantic Versioning <https://semver.org/>`_.

Have question or feedback?
--------------------------

Please post to `issues <https://github.com/commit-check/commit-check/issues>`_ for feedback, feature requests, or bug reports.

License
-------

This project is released under the `MIT License <https://github.com/commit-check/commit-check/blob/main/LICENSE>`_
