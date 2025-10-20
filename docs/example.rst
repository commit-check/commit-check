Usage Examples
==============

This guide demonstrates how to use commit-check to validate commit messages, branch names, and author information.

There are several ways to use commit-check: as a pre-commit hook, via STDIN, or directly with files.

Running as GitHub Action
------------------------

Please see `commit-check/commit-check-action <https://github.com/commit-check/commit-check-action>`_

Running as pre-commit hook
---------------------------

1. **Install pre-commit:**

.. tip::

    Make sure ``pre-commit`` is `installed <https://pre-commit.com/#install>`_.

.. code-block:: bash

    pip install pre-commit

2. **Create .pre-commit-config.yaml:**

.. code-block:: yaml

    -   repo: https://github.com/commit-check/commit-check
        rev: the tag or revision
        hooks:
        -   id: check-message
            stages: [commit-msg]
        -   id: check-branch
        -   id: check-author-name
        -   id: check-author-email

3. **Install the hooks:**

.. code-block:: bash

    pre-commit install --hook-type pre-commit --hook-type commit-msg

4. **Test the integration:**

.. code-block:: bash

    # This will trigger validation automatically
    git commit -m "feat: add new user authentication system"


Pre-commit Validation Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**✅ Successful Validation:**

.. code-block:: text

    $ git commit -m "feat: add user authentication system"

    check commit message.....................................................Passed
    check committer name.....................................................Passed
    check committer email....................................................Passed
    [main abc1234] feat: add user authentication system

**❌ Failed Validation:**

.. code-block:: text

    $ git commit -m "bad commit message"

    check commit message.....................................................Failed
    - hook id: check-message
    - exit code: 1

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

    Type message check failed ==> bad commit message
    It doesn't match regex: ^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .+
    The commit message should follow Conventional Commits. See https://www.conventionalcommits.org
    Suggest: Use <type>(<scope>): <description> with allowed types


Running as CLI
--------------

Commit-check provides several command-line options for different validation scenarios. via options or STDIN

.. tip ::
    Validate commit messages by piping them through STDIN. This is useful for testing or scripting.

Available Commands see `commit-check --help <cli_args.html>`_

Message Validation Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Validate message from STDIN
    echo "feat: new feature" | commit-check -m

    # Validate message from file
    commit-check -m commit_message.txt

    # Validate current git commit message (from git log)
    commit-check -m


**Reading from file:**

.. code-block:: bash

    # Create a commit message file
    cat > commit_message.txt << EOF
    fix(auth): resolve login timeout issue

    Users were experiencing timeouts during login.
    Increased session timeout and improved error handling.

    Fixes #123
    EOF

    # Validate from file
    commit-check -m commit_message.txt

    # Or pipe file content
    cat commit_message.txt | commit-check -m


Branch Validation Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Check current branch name
    commit-check --branch

    # Example valid branch names:
    # - feature/user-auth
    # - fix/login-bug
    # - hotfix/security-patch
    # - release/v1.2.0

Author Validation Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Check author name
    commit-check --author-name

    # Check author email
    commit-check --author-email

    # Check both author name and email
    commit-check --author-name --author-email


Configuration Examples
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Use custom configuration file
    echo "feat: test" | commit-check --config my-config.toml -m

    # Use configuration from different directory
    commit-check --config /path/to/config/cchk.toml -m


Valid Commit Message Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Basic feature
    echo "feat: add user registration" | commit-check -m

    # Feature with scope
    echo "feat(auth): implement OAuth2 login" | commit-check -m

    # Bug fix
    echo "fix: resolve memory leak in parser" | commit-check -m

    # Documentation update
    echo "docs: add installation guide" | commit-check -m

    # Breaking change
    echo "feat!: redesign API endpoints" | commit-check -m

    # Merge commit (automatically allowed)
    echo "Merge pull request #123 from feature/new-api" | commit-check -m

Invalid Commit Message Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # No type prefix
    echo "added new feature" | commit-check -m

    # Capitalized (if configured to disallow)
    echo "feat: Add new feature" | commit-check -m

    # Too short
    echo "fix" | commit-check -m

    # Non-imperative mood
    echo "feat: added login functionality" | commit-check -m

    # Unknown type
    echo "unknown: some changes" | commit-check -m

Error Output Examples
~~~~~~~~~~~~~~~~~~~~~

**Commit Message Validation Failure:**

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

**Branch Name Validation Failure:**

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

**Commit Signature Validation Failure:**

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

**Imperative Mood Validation Failure:**

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


Integration Tips
----------------

CI/CD Integration
~~~~~~~~~~~~~~~~~

You can use commit-check in CI/CD pipelines:

.. code-block:: bash

    # In your CI script
    git log --format="%s" -n 1 | commit-check -m

    # or just
    commit-check -m

Scripting
~~~~~~~~~

Use commit-check in scripts to validate commit messages programmatically:

.. code-block:: bash

    #!/bin/bash
    # validate-commits.sh

    # Get all commit messages from last 10 commits
    for i in {0..9}; do
        msg=$(git log --format="%s" -n 1 --skip=$i)
        if [ -n "$msg" ]; then
            echo "Validating: $msg"
            echo "$msg" | commit-check -m || exit 1
        fi
    done

    echo "All commits are valid!"

For more configuration options, see the `Configuration Documentation <configuration.html>`_.
