Commit Check
============

.. image:: https://img.shields.io/pypi/v/commit-check
    :alt: PyPI
    :target: https://pypi.org/project/commit-check/

.. image:: https://github.com/commit-check/commit-check/actions/workflows/CI.yml/badge.svg
    :alt: CI
    :target: https://github.com/commit-check/commit-check/actions/workflows/CI.yml

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

The reason behind it is that it is easier to read and enforces writing descriptive commits.
Besides that, having conventional commits and branch naming makes it possible to parse them and use them for something else, like:

- triggering specific types of builds
- generating automatically the version or a changelog
- easy to identify branch according to the branch type

Installation
------------

Global installation

.. code-block:: bash

    sudo pip3 install -U commit-check

User installation

.. code-block:: bash

    pip install -U commit-check


TODO: On macOS, it can also be installed via homebrew:

.. code-block:: bash

    brew install commit-check

Install from git repo

.. code-block:: bash

    pip install git+https://github.com/commit-check/commit-check.git@main


Usage
-----

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
- If you want to skip the ``commit-check``, you can use the option ``-n`` or ``--no-verify``.

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


Integrating with GitHub Action

.. code-block:: yaml

    name: commit-check

    on: pull_request

    jobs:
    commit-check:
        runs-on: ubuntu-latest
        steps:
        - uses: actions/checkout@v3
        - uses: commit-check/commit-check@v0
            id: check
            with:
            message: true
            branch: true

Example
-------

Check commit message failed

.. code-block:: bash

    Commit rejected by Commit-Check.

    (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)
    / ._. \      / ._. \      / ._. \      / ._. \      / ._. \
    __\( C )/__  __\( H )/__  __\( E )/__  __\( C )/__  __\( K )/__
    (_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)
    || E ||      || R ||      || R ||      || O ||      || R ||
    _.' `-' '._  _.' `-' '._  _.' `-' '._  _.' `-' '._  _.' `-' '.
    (.-./`-'\.-.)(.-./`-`\.-.)(.-./`-`\.-.)(.-./`-'\.-.)(.-./`-`\.-.)
    `-'     `-'  `-'     `-'  `-'     `-'  `-'     `-'  `-'     `-'

    Commit rejected.

    Invalid commit message. it does't match regex: ^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\\([\\w\\-\\.]+\\))?(!)?: ([\\w ])+([\\s\\S]*)

    The commit message should be structured as follows:

    <type>[optional scope]: <description>
    [optional body]
    [optional footer(s)]

    More details please refer to https://www.conventionalcommits.org


Check branch naming failed

.. code-block:: bash

    Commit rejected by Commit-Check.

    (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)    (c).-.(c)
    / ._. \      / ._. \      / ._. \      / ._. \      / ._. \
    __\( C )/__  __\( H )/__  __\( E )/__  __\( C )/__  __\( K )/__
    (_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)(_.-/'-'\-._)
    || E ||      || R ||      || R ||      || O ||      || R ||
    _.' `-' '._  _.' `-' '._  _.' `-' '._  _.' `-' '._  _.' `-' '.
    (.-./`-'\.-.)(.-./`-`\.-.)(.-./`-`\.-.)(.-./`-'\.-.)(.-./`-`\.-.)
    `-'     `-'  `-'     `-'  `-'     `-'  `-'     `-'  `-'     `-'

    Commit rejected.

    Invalid branch name. it does't match regex: ^(bugfix|feature|release|hotfix|task)\/.+|(master)|(main)

    Branches must begin with these types: bugfix/ feature/ release/ hotfix/ task/ or master main


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
