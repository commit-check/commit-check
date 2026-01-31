:status: new

Configuration
=============

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
