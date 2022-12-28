Commit Check
============

.. image:: https://img.shields.io/pypi/v/commit-check
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

Check commit message formatting, branch naming, referencing Jira tickets, and more

About
-----

commit-check is a tool designed for teams.

Its main purpose is to standardize the format of commit messages and branch naming.

The reason behind it is and makes it possible, like:

- writing descriptive commit is easy to read
- identify branch according to the branch type
- triggering specific type of commit/branch CI build
- automatically generate changelogs

Usage
-----

There are a variety of ways you can use commit-check:

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

Running as pre-commit hook
~~~~~~~~~~~~~~~~~~~~~~~~~~

Add .commit-check.yml

Create a config file ``.commit-check.yml`` under your repository, e.g. `.commit-check.yml <https://github.com/commit-check/commit-check/blob/main/.commit-check.yml>`_

The content of the config file should be in the following format.

.. code-block:: yaml

    checks:
    - check: message
        regex: '^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)'
        error: "<type>: <description>

        For Example. feat: Support new feature xxxx

        Between type and description MUST have a colon and space.

        More please refer to https://www.conventionalcommits.org"
    - check: branch
        regex: '^(bugfix|feature|release|hotfix|task)\/.+|(master)|(main)|(HEAD)|(PR-.+)'
        error: "Branches must begin with these types: bugfix/ feature/ release/ hotfix/ task/"

Use default configuration

- If you do not set ``.commit-check.yml``, ``commit-check`` will use the default configuration.
  i.e. the commit message will follow the rules of `conventional commits <https://www.conventionalcommits.org/en/v1.0.0/#summary>`_,
  branch naming follow bitbucket `branching model <https://support.atlassian.com/bitbucket-cloud/docs/configure-a-projects-branching-model/>`_.

Integrating with pre-commit

.. tip::

    Make sure ``pre-commit`` is `installed <https://pre-commit.com/#install>`_.

Install the commit-msg hook in your project repo.

.. code-block:: bash

    pre-commit install --hook-type prepare-commit-msg

Or have ``default_install_hook_types: [pre-commit, prepare-commit-msg]`` in your ``.pre-commit-config.yaml``.

.. code-block:: yaml

    default_install_hook_types: [pre-commit, prepare-commit-msg]

    -   repo: https://github.com/commit-check/commit-check
        rev: v0.1.4
        hooks:
        -   id: check-message
        -   id: check-branch

Running as GitHub Action
~~~~~~~~~~~~~~~~~~~~~~~~

Please see `commit-check/commit-check-action <https://github.com/commit-check/commit-check-action>`_

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
    Suggest to run => git commit --amend


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

.. image:: https://ko-fi.com/img/githubbutton_sm.svg
    :target: https://ko-fi.com/H2H85WC9L
    :alt: ko-fi
