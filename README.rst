Commit Check
============

.. image:: https://img.shields.io/pypi/v/commit-check?logo=python&logoColor=white
    :alt: PyPI
    :target: https://pypi.org/project/commit-check/

.. image:: https://github.com/commit-check/commit-check/actions/workflows/main.yml/badge.svg
    :alt: CI
    :target: https://github.com/commit-check/commit-check/actions/workflows/main.yml

.. image:: https://sonarcloud.io/api/project_badges/measure?project=commit-check_commit-check&metric=alert_status
    :alt: Quality Gate Status
    :target: https://sonarcloud.io/summary/new_code?id=commit-check_commit-check

.. image:: https://results.pre-commit.ci/badge/github/commit-check/commit-check/main.svg
    :alt: pre-commit.ci status
    :target: https://results.pre-commit.ci/latest/github/commit-check/commit-check/main

.. image:: https://codecov.io/gh/commit-check/commit-check/branch/main/graph/badge.svg?token=GC2U5V5ZRT
    :alt: CodeCov
    :target: https://codecov.io/gh/commit-check/commit-check

Overview
--------

Check commit message formatting, branch naming, committer name, email, and more. The open-source alternative to Yet Another Commit Checker.

- requiring commit message to match regex
- requiring branch naming to match regex
- requiring committer name and email to match regex
- customizing error message
- customizing suggest command

Purpose
-------

commit-check is a tool designed for teams.

Its main purpose is to standardize the format of commit message, branch naming, etc, and makes it possible to:

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

- If you did't set ``.commit-check.yml``, ``commit-check`` will use the `default configuration <https://github.com/commit-check/commit-check/blob/main/commit_check/__init__.py#L15-L39>`_.

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
        hooks:
        -   id: check-message
        -   id: check-branch

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
    Suggest to run => git commit --amend --no-verify


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
    Suggest to run => git checkout -b type/branch_name


Versioning
----------

Versioning follows `Semantic Versioning <https://semver.org/>`_.

Have question or feedback?
--------------------------

To provide feedback (requesting a feature or reporting a bug) please post to `issues <https://github.com/commit-check/commit-check/issues>`_.

License
-------

The scripts and documentation in this project are released under the `MIT License <https://github.com/commit-check/commit-check/blob/main/LICENSE>`_

If my open source projects are useful for your **product/company** you can also sponsor my work on them ☕

.. image:: https://ko-fi.com/img/githubbutton_sm.svg
    :target: https://ko-fi.com/H2H85WC9L
    :alt: ko-fi
