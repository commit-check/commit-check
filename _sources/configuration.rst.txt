Configuration
=============

``commit-check`` configuration file support TOML format.

See ``cchk.toml`` for the default configuration values.


commit-check can be configured via a ``cchk.toml`` or ``commit-check.toml`` file.

The file should be placed in the root of your repository.

.. code-block:: toml

    [commit]
    # https://www.conventionalcommits.org
    conventional_commits = true
    subject_capitalized = true
    subject_imperative = true
    subject_max_length = 50
    subject_min_length = 5
    allow_commit_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore"]
    allow_merge_commits = true
    allow_revert_commits = true
    allow_empty_commits = false
    allow_fixup_commits = true
    allow_wip_commits = false
    require_body = false
    allow_authors = []
    ignore_authors = ["dependabot[bot]", "dependabot-preview[bot]"]
    require_signed_off_by = true
    required_signoff_name = "Your Name"
    required_signoff_email = "your.email@example.com"

    [branch]
    # https://conventional-branch.github.io/
    conventional_branch = true
    allow_branch_types = ["feature", "bugfix", "hotfix", "release", "chore", "feat", "fix"]
    require_rebase_target = "main"



options table description
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
     - Subject must be in imperative mood.
   * - commit
     - subject_max_length
     - int
     - 50
     - Maximum length of the subject line.
   * - commit
     - subject_min_length
     - int
     - 5
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
   * - author
     - allow_authors
     - list[str]
     - []
     - List of allowed authors. If empty, all authors are allowed except those in ignore_authors.
   * - author
     - ignore_authors
     - list[str]
     - ["dependabot[bot]", "dependabot-preview[bot]"]
     - List of authors to ignore (i.e., always allow).
   * - author
     - require_signed_off_by
     - bool
     - true
     - Require "Signed-off-by" line in the commit message footer.
