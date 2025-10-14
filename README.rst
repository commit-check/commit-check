Commit Check
============

.. |pypi-version| image:: https://img.shields.io/pypi/v/commit-check?logo=python&logoColor=white&color=%232c9ccd
    :target: https://pypi.org/project/commit-check/
    :alt: PyPI

.. |ci-badge| image:: https://github.com/commit-check/commit-check/actions/workflows/main.yml/badge.svg
    :target: https://github.com/commit-check/commit-check/actions/workflows/main.yml
    :alt: CI

.. |sonar-badge| image:: https://sonarcloud.io/api/project_badges/measure?project=commit-check_commit-check&metric=alert_status&color=%232c9ccd
    :target: https://sonarcloud.io/summary/new_code?id=commit-check_commit-check
    :alt: Quality Gate Status

.. |codecov-badge| image:: https://codecov.io/gh/commit-check/commit-check/branch/main/graph/badge.svg?token=GC2U5V5ZRT&color=%232c9ccd
    :target: https://codecov.io/gh/commit-check/commit-check
    :alt: CodeCov

.. |commit-check-badge| image:: https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white&color=%232c9ccd
    :target: https://github.com/commit-check/commit-check
    :alt: commit-check

.. |slsa-badge| image:: https://slsa.dev/images/gh-badge-level3.svg?color=%232c9ccd
    :target: https://slsa.dev
    :alt: SLSA

|pypi-version| |ci-badge| |sonar-badge| |commit-check-badge| |codecov-badge| |slsa-badge|

Overview
--------

**Commit Check** (aka **cchk**) is an open-source tool that enforces commit metadata standards — including commit messages, branch naming, committer name/email, commit signoff, and more — to ensure consistency and compliance across teams.

As an alternative to GitHub Enterprise `Metadata restrictions <https://docs.github.com/en/enterprise-server@3.11/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#metadata-restrictions>`_
and Bitbucket's paid plugin `Yet Another Commit Checker <https://marketplace.atlassian.com/apps/1211854/yet-another-commit-checker?tab=overview&hosting=datacenter>`_, Commit Check stands out by integrating DevOps principles and Infrastructure as Code (IaC) practices.

What’s New in v2.0.0
--------------------

Version 2.0.0 is a major release featuring a new configuration format, a modernized architecture, and an improved user experience.

**✨ Highlights**

* **TOML Configuration** — Replaces ``.commit-check.yml`` with ``cchk.toml`` or ``commit-check.toml`` for clearer, more consistent syntax.
* **Simplified CLI & Hooks** — Legacy pre-commit hooks and options removed to deliver a cleaner, more streamlined interface.
* **New Validation Engine** — Fully redesigned for greater flexibility, performance, and maintainability.

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


Configuration
-------------

Use Default Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

- **Commit Check** uses a `default configuration <https://github.com/commit-check/commit-check/blob/main/docs/configuration.rst>`_ if you do not provide a ``cchk.toml`` or ``commit-check.toml`` file.

- The default configuration is lenient — it only checks whether commit messages follow the `Conventional Commits <https://www.conventionalcommits.org/en/v1.0.0/#summary>`_ specification and branch names follow the `Conventional Branch <https://conventional-branch.github.io/#summary>`_ convention.

Use Custom Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

To customize the behavior, create a configuration file named ``cchk.toml`` or ``commit-check.toml`` in your repository's root directory, e.g., `cchk.toml <https://github.com/commit-check/commit-check/blob/main/cchk.toml>`_

Usage
-----

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
    It doesn't match regex: ^(chore|ci|docs|feat|fix|refactor|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)|(Merge).*|(fixup!.*)
    The commit message should follow Conventional Commits. See https://www.conventionalcommits.org
    Suggest: Use <type>(<scope>): <description> with allowed types


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
    It doesn't match regex: ^(feature|bugfix|hotfix|release|chore|feat|fix)\/.+|(master)|(main)|(HEAD)|(PR-.+)
    The branch should follow Conventional Branch. See https://conventional-branch.github.io/
    Suggest: Use <type>/<description> with allowed types or ignore_authors in config branch section to bypass

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
