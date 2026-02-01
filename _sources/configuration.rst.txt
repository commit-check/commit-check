:status: new

Configuration
=============

``commit-check`` can be configured in three ways with the following priority (highest to lowest):

1. **Command-line arguments** (``--subject-imperative=true``)
2. **Environment variables** (``CCHK_SUBJECT_IMPERATIVE=true``)
3. **Configuration files** (``cchk.toml`` or ``commit-check.toml``)
4. **Built-in defaults**

This flexibility allows you to:

* Use configuration files for project-wide settings
* Override with environment variables in CI/CD pipelines
* Override specific settings via CLI for one-off checks
* Use without any configuration files (relies on defaults)

Configuration Files
-------------------

``commit-check`` configuration files support the TOML format. See ``cchk.toml`` for an example configuration.

.. tip::
  **Default Behavior**

  * When no configuration file exists, commit-check uses sensible defaults with minimal restrictions.
  * Only conventional commits format, subject capitalization, and imperative mood are enforced by default.
  * No length limits, author restrictions, or rebase requirements are applied.

commit-check can be configured via a ``cchk.toml`` or ``commit-check.toml`` file.

The file should be placed in the root of your repository or in the ``.github`` folder.

Configuration File Locations
-----------------------------

commit-check searches for configuration files in the following order (first found is used):

1. ``cchk.toml`` (root directory)
2. ``commit-check.toml`` (root directory)
3. ``.github/cchk.toml``
4. ``.github/commit-check.toml``

.. tip::
  **GitHub Best Practice**

  Placing configuration files in the ``.github`` folder helps keep your repository root clean and follows GitHub conventions used by tools like Dependabot and Renovate.

Example Configuration
---------------------

.. code-block:: toml
    :class: copy

    [commit]
    # https://www.conventionalcommits.org
    conventional_commits = true
    subject_capitalized = false
    subject_imperative = false
    # subject_max_length = 50  # Optional - no limit by default
    # subject_min_length = 5   # Optional - no limit by default
    allow_commit_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore"]
    allow_merge_commits = true
    allow_revert_commits = true
    allow_empty_commits = false
    allow_fixup_commits = true
    allow_wip_commits = false
    require_body = false
    # ignore_authors = []      # Optional - no authors ignored by default
    require_signed_off_by = false
    # required_signoff_name = "Your Name"      # Optional
    # required_signoff_email = "your.email@example.com"  # Optional

    [branch]
    # https://conventional-branch.github.io/
    conventional_branch = true
    allow_branch_types = ["feature", "bugfix", "hotfix", "release", "chore", "feat", "fix"]
    # allow_branch_names = []  # Optional - additional standalone branch names (e.g., ["develop", "staging"])
    # require_rebase_target = "main"  # Optional - no rebase requirement by default
    # ignore_authors = []      # Optional - no authors ignored by default


Command-Line Arguments
----------------------

All configuration options can be specified via command-line arguments, which take precedence over environment variables and configuration files.

**Syntax:**

* Boolean options: ``--option-name=true`` or ``--option-name=false``
* Integer options: ``--option-name=80``
* List options: ``--option-name=value1,value2,value3`` (comma-separated)
* String options: ``--option-name=value``

**Examples:**

.. code-block:: bash

    # Disable imperative mood check
    commit-check --message --subject-imperative=false

    # Set custom subject length limit
    commit-check --message --subject-max-length=72

    # Restrict allowed commit types
    commit-check --message --allow-commit-types=feat,fix,docs

    # Combine multiple options
    commit-check --message --subject-imperative=true --subject-max-length=50 --allow-commit-types=feat,fix

    # Branch configuration via CLI
    commit-check --branch --allow-branch-types=feature,bugfix,hotfix

**Pre-commit Hook Usage:**

The primary use case for CLI arguments is configuring commit-check in ``.pre-commit-config.yaml`` without requiring a TOML file:

.. code-block:: yaml

    repos:
      - repo: https://github.com/commit-check/commit-check
        rev: v2.3.0
        hooks:
          - id: commit-check
            args:
              - --subject-imperative=false
              - --subject-max-length=100
              - --allow-merge-commits=false

Environment Variables
---------------------

Configuration can also be set via environment variables with the ``CCHK_`` prefix. This is useful for CI/CD pipelines and temporary overrides.

**Naming Convention:**

* Convert option name to uppercase
* Replace hyphens with underscores
* Add ``CCHK_`` prefix

**Examples:**

.. code-block:: bash

    # Set boolean options
    export CCHK_SUBJECT_IMPERATIVE=true
    export CCHK_SUBJECT_CAPITALIZED=false

    # Set integer options
    export CCHK_SUBJECT_MAX_LENGTH=72
    export CCHK_SUBJECT_MIN_LENGTH=10

    # Set list options (comma-separated)
    export CCHK_ALLOW_COMMIT_TYPES=feat,fix,docs,chore
    export CCHK_ALLOW_BRANCH_TYPES=feature,bugfix,hotfix

    # Set string options
    export CCHK_REQUIRE_REBASE_TARGET=main

    # Use in CI/CD
    CCHK_SUBJECT_MAX_LENGTH=100 commit-check --message

**Complete Mapping:**

.. list-table::
   :header-rows: 1

   * - TOML Config
     - Environment Variable
     - CLI Argument
   * - ``conventional_commits = true``
     - ``CCHK_CONVENTIONAL_COMMITS=true``
     - ``--conventional-commits=true``
   * - ``subject_capitalized = false``
     - ``CCHK_SUBJECT_CAPITALIZED=false``
     - ``--subject-capitalized=false``
   * - ``subject_imperative = true``
     - ``CCHK_SUBJECT_IMPERATIVE=true``
     - ``--subject-imperative=true``
   * - ``subject_max_length = 80``
     - ``CCHK_SUBJECT_MAX_LENGTH=80``
     - ``--subject-max-length=80``
   * - ``subject_min_length = 5``
     - ``CCHK_SUBJECT_MIN_LENGTH=5``
     - ``--subject-min-length=5``
   * - ``allow_commit_types = ["feat", "fix"]``
     - ``CCHK_ALLOW_COMMIT_TYPES=feat,fix``
     - ``--allow-commit-types=feat,fix``
   * - ``allow_merge_commits = true``
     - ``CCHK_ALLOW_MERGE_COMMITS=true``
     - ``--allow-merge-commits=true``
   * - ``allow_revert_commits = true``
     - ``CCHK_ALLOW_REVERT_COMMITS=true``
     - ``--allow-revert-commits=true``
   * - ``allow_empty_commits = false``
     - ``CCHK_ALLOW_EMPTY_COMMITS=false``
     - ``--allow-empty-commits=false``
   * - ``allow_fixup_commits = true``
     - ``CCHK_ALLOW_FIXUP_COMMITS=true``
     - ``--allow-fixup-commits=true``
   * - ``allow_wip_commits = false``
     - ``CCHK_ALLOW_WIP_COMMITS=false``
     - ``--allow-wip-commits=false``
   * - ``require_body = false``
     - ``CCHK_REQUIRE_BODY=false``
     - ``--require-body=false``
   * - ``require_signed_off_by = false``
     - ``CCHK_REQUIRE_SIGNED_OFF_BY=false``
     - ``--require-signed-off-by=false``
   * - ``ignore_authors = ["bot"]``
     - ``CCHK_IGNORE_AUTHORS=bot,user``
     - ``--ignore-authors=bot,user``
   * - ``conventional_branch = true``
     - ``CCHK_CONVENTIONAL_BRANCH=true``
     - ``--conventional-branch=true``
   * - ``allow_branch_types = ["feature"]``
     - ``CCHK_ALLOW_BRANCH_TYPES=feature,bugfix``
     - ``--allow-branch-types=feature,bugfix``
   * - ``allow_branch_names = ["develop"]``
     - ``CCHK_ALLOW_BRANCH_NAMES=develop,staging``
     - ``--allow-branch-names=develop,staging``
   * - ``require_rebase_target = "main"``
     - ``CCHK_REQUIRE_REBASE_TARGET=main``
     - ``--require-rebase-target=main``
   * - ``ignore_authors = ["bot"]`` (in branch section)
     - ``CCHK_BRANCH_IGNORE_AUTHORS=bot,user``
     - ``--branch-ignore-authors=bot,user``


Configuration Priority Example
-------------------------------

When the same option is specified in multiple places, the priority determines which value is used:

.. code-block:: bash

    # In cchk.toml:
    # subject_max_length = 100

    # Set via environment:
    export CCHK_SUBJECT_MAX_LENGTH=80

    # Override via CLI:
    commit-check --message --subject-max-length=50

    # Result: subject_max_length = 50 (CLI wins)


Options Table Description
-------------------------

.. list-table::
   :header-rows: 1

   * - Section
     - Option
     - Type
     - Default
     - Description
   * - commit
     - conventional_commits
     - bool
     - true
     - Enforce Conventional Commits specification.
   * - commit
     - subject_capitalized
     - bool
     - true
     - Subject must start with a capital letter.
   * - commit
     - subject_imperative
     - bool
     - true
     - Subject must be in imperative mood. Forms of verbs can be found at `imperatives.py <https://github.com/commit-check/commit-check/blob/main/commit_check/imperatives.py>`_
   * - commit
     - subject_max_length
     - int
     - None (no limit)
     - Maximum length of the subject line.
   * - commit
     - subject_min_length
     - int
     - None (no limit)
     - Minimum length of the subject line.
   * - commit
     - allow_commit_types
     - list[str]
     - ["feat", "fix", "docs", "style", "refactor", "test", "chore"]
     - Allowed commit types when conventional_commits is true.
   * - commit
     - allow_merge_commits
     - bool
     - true
     - Allow merge commits.
   * - commit
     - allow_revert_commits
     - bool
     - true
     - Allow revert commits.
   * - commit
     - allow_empty_commits
     - bool
     - false
     - Allow empty commits.
   * - commit
     - allow_fixup_commits
     - bool
     - true
     - Allow fixup commits (e.g., "fixup! <commit message>").
   * - commit
     - allow_wip_commits
     - bool
     - false
     - Allow work-in-progress commits (e.g., "WIP: <commit message>").
   * - commit
     - require_body
     - bool
     - false
     - Require a body in the commit message.
   * - commit
     - ignore_authors
     - list[str]
     - [] (none ignored)
     - List of authors to ignore (i.e., always allow).
   * - commit
     - require_signed_off_by
     - bool
     - false
     - Require "Signed-off-by" line in the commit message footer.
   * - branch
     - conventional_branch
     - bool
     - true
     - Enforce Conventional Branch specification.
   * - branch
     - allow_branch_types
     - list[str]
     - ["feature", "bugfix", "hotfix", "release", "chore", "feat", "fix"]
     - Allowed branch types when conventional_branch is true.
   * - branch
     - allow_branch_names
     - list[str]
     - [] (empty list)
     - Additional standalone branch names allowed when conventional_branch is true (e.g., ["develop", "staging"]). By default, master, main, HEAD, and PR-* are always allowed.
   * - branch
     - require_rebase_target
     - str
     - None (no requirement)
     - Target branch for rebase requirement. If not set, no rebase validation is performed.
   * - branch
     - ignore_authors
     - list[str]
     - [] (none ignored)
     - List of authors to ignore (i.e., always allow).
