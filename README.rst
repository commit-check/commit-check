Commit Check
============

.. image:: https://img.shields.io/pypi/v/commit-check?logo=python&logoColor=white
    :target: https://pypi.org/project/commit-check/
    :alt: PyPI

.. image:: https://github.com/commit-check/commit-check/actions/workflows/main.yml/badge.svg
    :target: https://github.com/commit-check/commit-check/actions/workflows/main.yml
    :alt: CI

.. image:: https://sonarcloud.io/api/project_badges/measure?project=commit-check_commit-check&metric=alert_status
    :target: https://sonarcloud.io/summary/new_code?id=commit-check_commit-check
    :alt: Quality Gate Status

.. image:: https://codecov.io/gh/commit-check/commit-check/branch/main/graph/badge.svg?token=GC2U5V5ZRT
    :target: https://codecov.io/gh/commit-check/commit-check
    :alt: CodeCov

.. image:: https://img.shields.io/badge/commit--check-enabled-brightgreen?logo=Git&logoColor=white
    :target: https://github.com/commit-check/commit-check
    :alt: commit-check

.. image:: https://slsa.dev/images/gh-badge-level3.svg
    :target: https://slsa.dev
    :alt: SLSA

Overview
--------

Commit Check is open source alternative to Yet Another Commit Checker.

It supports checking commit message, branch naming, committer name/email, commit signoff and customizing error message and suggest command (tell me more, please).

commit-check is a tool designed for teams. Its main purpose is to standardize the format of commit message, branch naming, etc, and makes it possible to:

- writing descriptive commit is easy to read
- identify branch according to the branch type
- triggering the specific types of commit/branch CI build
- automatically generate changelogs

Configuration
-------------

Use custom configuration
~~~~~~~~~~~~~~~~~~~~~~~~

Create a config file ``.commit-check.yml`` under your repository root directory, e.g. `.commit-check.yml <https://github.com/commit-check/commit-check/blob/main/.commit-check.yml>`_

Use default configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

- If you did't set ``.commit-check.yml``, ``commit-check`` will use the `default configuration <https://github.com/commit-check/commit-check/blob/main/commit_check/__init__.py>`_.

- i.e. the commit message will follow the rules of `conventional commits <https://www.conventionalcommits.org/en/v1.0.0/#summary>`_,
  branch naming follow bitbucket `branching model <https://support.atlassian.com/bitbucket-cloud/docs/configure-a-projects-branching-model/>`_.


Usage
-----

There are a variety of ways you can use commit-check as follows.

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
        -   id: check-message
        -   id: check-branch
        -   id: check-author-name
        -   id: check-author-email
        -   id: check-commit-signoff

Running as CLI
~~~~~~~~~~~~~~

Global installation

.. code-block:: bash

    sudo pip3 install -U commit-check

User installation

.. code-block:: bash

    pip install -U commit-check

Install from git repo

.. code-block:: bash

    pip install git+https://github.com/commit-check/commit-check.git@main

Then you can run ``commit-check`` command line. More about ``commit-check --help`` please see `docs <https://commit-check.github.io/commit-check/cli_args.html>`_.

Running as Git Hooks
~~~~~~~~~~~~~~~~~~~~

To configure the hook, you need to create a new script file in the ``.git/hooks/`` directory of your Git repository.

Here is an example script that you can use to set up the hook:

.. code-block:: bash

    #!/bin/sh
    commit-check --message --branch --author-name --author-email

Save the script file to ``pre-push`` and make it executable by running the following command:

.. code-block:: bash

    chmod +x .git/hooks/pre-push

Then when you run ``git push`` command, this push hook will be run automatically.

Example
-------

Check commit message failed

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

    Invalid commit message => test
    It doesn't match regex: ^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)

    The commit message should be structured as follows:

    <type>[optional scope]: <description>
    [optional body]
    [optional footer(s)]

    More details please refer to https://www.conventionalcommits.org
    Suggest: please check your commit message whether matches above regex


Check branch naming failed

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

    Invalid branch name => test
    It doesn't match regex: ^(bugfix|feature|release|hotfix|task)\/.+|(master)|(main)|(HEAD)|(PR-.+)

    Branches must begin with these types: bugfix/ feature/ release/ hotfix/ task/
    Suggest: run command `git checkout -b type/branch_name`


Badging your repository
-----------------------

You can add a badge to your repository to show your contributors / users that you use commit-check!

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

To provide feedback (requesting a feature or reporting a bug) please post to `issues <https://github.com/commit-check/commit-check/issues>`_.

License
-------

This project is released under the `MIT License <https://github.com/commit-check/commit-check/blob/main/LICENSE>`_
