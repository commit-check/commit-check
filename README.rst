Commit Check
============

.. |pypi-version| image:: https://img.shields.io/pypi/v/commit-check?logo=python&logoColor=white
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

.. |commit-check-badge| image:: https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white
    :target: https://github.com/commit-check/commit-check
    :alt: commit-check

.. |slsa-badge| image:: https://slsa.dev/images/gh-badge-level3.svg
    :target: https://slsa.dev
    :alt: SLSA

|pypi-version| |ci-badge| |sonar-badge| |codecov-badge| |commit-check-badge| |slsa-badge|

Overview
--------

**Commit Check** is a free, powerful tool that enforces commit metadata standards, including commit message, branch naming, committer name/email, commit signoff and more.

Fully customizable with error messages and suggested commands, it ensures compliance across teams.

As an alternative to GitHub Enterprise `Metadata restrictions <https://docs.github.com/en/enterprise-server@3.11/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#metadata-restrictions>`_ and Bitbucket's paid plugin `Yet Another Commit Checker <https://marketplace.atlassian.com/apps/1211854/yet-another-commit-checker?tab=overview&hosting=datacenter>`_, Commit Check stands out by integrating DevOps principles and Infrastructure as Code (IaC).

Configuration
-------------

Use Default Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

- **Commit Check** uses a `default configuration <https://github.com/commit-check/commit-check/blob/main/docs/configuration.rst>`_ if you do not provide a ``cchk.toml`` or ``commit-check.toml`` file.

- The default configuration enforces commit message rules based on the `Conventional Commits <https://www.conventionalcommits.org/en/v1.0.0/#summary>`_ specification and branch naming rules based on the `Conventional Branch <https://conventional-branch.github.io/#summary>`_ convention.

Use Custom Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

To customize the behavior, create a config file ``cchk.toml`` or ``commit-check.toml`` under your repository's root directory, e.g., `cchk.toml <https://github.com/commit-check/commit-check/blob/main/cchk.toml>`_

Usage
-----

Running as GitHub Action
~~~~~~~~~~~~~~~~~~~~~~~~

Please see `commit-check/commit-check-action <https://github.com/commit-check/commit-check-action>`_

Running as pre-commit hook
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. tip::

    Make sure ``pre-commit`` is `installed <https://pre-commit.com/#install>`_.

.. code-block:: yaml

    -   repo: https://github.com/commit-check/commit-check
        rev: the tag or revision
        hooks: # support hooks
        -   id: check-message  # requires commit-msg hook
        -   id: check-branch
        -   id: check-author-name
        -   id: check-author-email

Running as CLI
~~~~~~~~~~~~~~

Install globally

.. code-block:: bash

    sudo pip3 install -U commit-check

Install locally

.. code-block:: bash

    pip install -U commit-check

Install from source code

.. code-block:: bash

    pip install git+https://github.com/commit-check/commit-check.git@main

Then, run ``commit-check --help`` or ``cchk --help`` (alias for ``commit-check``) from the command line.

For more information, see the `docs <https://commit-check.github.io/commit-check/cli_args.html>`_.

Running as Git Hooks
~~~~~~~~~~~~~~~~~~~~

To configure the hook, create a script file in the ``.git/hooks/`` directory.

.. code-block:: bash

    #!/bin/sh
    commit-check --message --branch --author-name --author-email

Save the script file as ``pre-push`` and make it executable:

.. code-block:: bash

    chmod +x .git/hooks/pre-push

Now, ``git push`` will trigger this hook automatically.

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
    The branch should follow Conventional Branch. See https://conventional-branches.github.io/
    Suggest: git checkout -b <type>/<branch_name>


Check Commit Signature Failed

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

    Type require_signed_off_by check failed ==> fix: add missing file
    It doesn't match regex: Signed-off-by:.*[A-Za-z0-9]\s+<.+@.+>
    Signed-off-by not found in latest commit
    Suggest: git commit --amend --signoff or use --signoff on commit


Check Imperative Mood Failed

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

    Type imperative check failed ==> fix: added missing file
    It doesn't match regex:
    Commit message should use imperative mood (e.g., 'Add feature' not 'Added feature')
    Suggest: Use imperative mood in the subject line


And many more... see `commit-check.toml <cchk.toml>`_ for all available checks.

Badging your repository
-----------------------

You can add a badge to your repository to show that you use commit-check!

.. image:: https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white
    :target: https://github.com/commit-check/commit-check
    :alt: commit-check

Markdown

.. code-block:: text

    [![commit-check](https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white)](https://github.com/commit-check/commit-check)

reStructuredText

.. code-block:: text

    .. image:: https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white
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
