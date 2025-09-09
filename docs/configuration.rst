Configuration
=============

``commit-check`` configuration file support TOML format.

See ``cchk.toml`` for the default configuration values.


commit-check can be configured via a ``cchk.toml``, ``commit-check.toml``, or in ``pyproject.toml`` file.

The file should be placed in the root of your repository.

.. code-block:: toml

    [commit]
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

    [branch]
    conventional_branch = true
    allow_branch_types = ["feature", "bugfix", "hotfix"]
    require_rebase_target = "main"

    [author]
    allow_authors = []
    ignore_authors = ["dependabot[bot]", "dependabot-preview[bot]"]

    [signed-off-by]
    require_signed_off_by = true
    required_signoff_name = "Your Name"
    required_signoff_email = "your.email@example.com"
