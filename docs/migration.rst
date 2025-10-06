:status: new

Migration Guide
===============

This guide helps you migrate from commit-check v1.x (YAML configuration) to v2.0+ (TOML configuration).

Overview
--------

Version 2.0 introduces significant changes to commit-check:

* **Configuration format**: ``.commit-check.yml`` → ``cchk.toml`` or ``commit-check.toml``
* **Simplified architecture**: New validation engine with cleaner design
* **Enhanced functionality**: Better error messages and more flexible configuration options

Quick Migration Steps
---------------------

1. **Backup your existing configuration**:

   .. code-block:: bash

       cp .commit-check.yml .commit-check.yml.backup

2. **Create new TOML configuration**:

   .. code-block:: bash

       touch cchk.toml  # or commit-check.toml

3. **Convert YAML to TOML format** (see examples below)

4. **Test the new configuration**:

   .. code-block:: bash

       commit-check --help
       commit-check --message --branch --author-name --author-email --dry-run

5. **Remove old YAML file**:

   .. code-block:: bash

       rm .commit-check.yml.backup  # after confirming everything works

Configuration Format Changes
----------------------------

The configuration structure has changed from YAML to TOML format

YAML (v1.x) vs TOML (v2.0+)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Old YAML format** (``.commit-check.yml``):

.. code-block:: yaml

    checks:
    - check: message
        regex: '^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test){1}(\([\w\-\.]+\))?(!)?: ([\w ])+([\s\S]*)|(Merge).*|(fixup!.*)'
        error: "The commit message should be structured as follows:\n\n
        <type>[optional scope]: <description>\n
        [optional body]\n
        [optional footer(s)]\n\n
        More details please refer to https://www.conventionalcommits.org"
        suggest: please check your commit message whether matches above regex

    - check: branch
        regex: ^(bugfix|feature|release|hotfix|task|chore)\/.+|(master)|(main)|(HEAD)|(PR-.+)
        error: "Branches must begin with these types: bugfix/ feature/ release/ hotfix/ task/ chore/"
        suggest: run command `git checkout -b type/branch_name`

    - check: author_name
        regex: ^[A-Za-zÀ-ÖØ-öø-ÿ\u0100-\u017F\u0180-\u024F ,.\'-]+$|.*(\[bot])
        error: The committer name seems invalid
        suggest: run command `git config user.name "Your Name"`

    - check: author_email
        regex: ^.+@.+$
        error: The committer email seems invalid
        suggest: run command `git config user.email yourname@example.com`

    - check: commit_signoff
        regex: Signed-off-by:.*[A-Za-z0-9]\s+<.+@.+>
        error: Signed-off-by not found in latest commit
        suggest: run command `git commit -m "conventional commit message" --signoff`

    - check: merge_base
        regex: main # it can be master, develop, devel etc based on your project.
        error: Current branch is not rebased onto target branch
        suggest: Please ensure your branch is rebased with the target branch

    - check: imperative
        regex: '' # Not used for imperative mood check
        error: 'Commit message should use imperative mood (e.g., "Add feature" not "Added feature")'
        suggest: 'Use imperative mood in commit message like "Add", "Fix", "Update", "Remove"'

**New TOML format** (``cchk.toml`` or ``commit-check.toml``):

.. code-block:: toml

    [commit]
    # https://www.conventionalcommits.org
    conventional_commits = true
    subject_capitalized = false
    subject_imperative = true
    subject_max_length = 80
    subject_min_length = 5
    allow_commit_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore", "ci"]
    allow_merge_commits = true
    allow_revert_commits = true
    allow_empty_commits = false
    allow_fixup_commits = true
    allow_wip_commits = false
    require_body = false
    require_signed_off_by = false
    ignore_authors = ["dependabot[bot]", "copilot[bot]"]

    [branch]
    # https://conventional-branch.github.io/
    conventional_branch = true
    allow_branch_types = ["feature", "bugfix", "hotfix", "release", "chore", "feat", "fix"]
    require_rebase_target = "main"



CLI Changes
~~~~~~~~~~~

The command-line interface has been simplified:

**Old CLI** (v1.x):

.. code-block:: bash

    commit-check --config .commit-check.yml

**New CLI** (v2.0+):

.. code-block:: bash

    commit-check --config cchk.toml  # or commit-check.toml
    # Or use defaults (no config file needed)
    commit-check --message --branch


Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Issue**: "Configuration file not found"

**Solution**: Ensure your file is named ``cchk.toml`` or ``commit-check.toml`` and placed in the repository root.

**Issue**: "Invalid TOML syntax"

**Solution**: Use a TOML validator or check the syntax. Common issues include:

* Missing quotes around strings
* Incorrect boolean values (use ``true``/``false``, not ``True``/``False``)
* Invalid array syntax

**Issue**: "Validation rules not working as expected"

**Solution**: Check the `Configuration Documentation <configuration.html>`_ for the correct option names and formats.

Validation and Testing
~~~~~~~~~~~~~~~~~~~~~~

After migration, test your configuration:

.. code-block:: bash

    # Test commit message validation
    echo "feat: test commit message" | commit-check --message

    # Test branch validation
    commit-check --branch

    # Test with dry-run flag
    commit-check --message --branch --author-name --author-email --dry-run

Getting Help
------------

* **Documentation**: Check the `Configuration Guide <configuration.html>`_
* **Issues**: Report problems on `GitHub Issues <https://github.com/commit-check/commit-check/issues>`_
