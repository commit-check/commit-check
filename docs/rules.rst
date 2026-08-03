Rules Reference
===============

Every check that can report a failure has a **stable rule ID**. Rule IDs never
change once released, so they are safe to reference in documentation, code
review comments, and tooling.

Rule IDs appear in commit-check output and in ``--format json`` results:

.. code-block:: text

    CC003 subject_imperative check failed ==> docs: revamped the profile

ID ranges
---------

.. list-table::
   :header-rows: 1

   * - Range
     - Category
   * - ``CC0xx``
     - Commit message
   * - ``CC1xx``
     - Author
   * - ``CC2xx``
     - Branch
   * - ``CC3xx``
     - Push

All rules
---------

.. list-table::
   :header-rows: 1

   * - ID
     - Name
     - Description
   * - :ref:`CC001 <cc001>`
     - ``message``
     - The commit message should follow Conventional Commits
   * - :ref:`CC002 <cc002>`
     - ``subject-capitalized``
     - Subject must start with a capital letter
   * - :ref:`CC003 <cc003>`
     - ``subject-imperative``
     - Commit message should use imperative mood (e.g., 'fix bug' not 'fixed bug', 'add feature' not 'adding feature')
   * - :ref:`CC004 <cc004>`
     - ``subject-max-length``
     - Subject must be at most {max_len} characters
   * - :ref:`CC005 <cc005>`
     - ``subject-min-length``
     - Subject must be at least {min_len} characters
   * - :ref:`CC006 <cc006>`
     - ``allow-merge-commits``
     - Merge commits are not allowed
   * - :ref:`CC007 <cc007>`
     - ``allow-revert-commits``
     - Revert commits are not allowed
   * - :ref:`CC008 <cc008>`
     - ``allow-empty-commits``
     - Empty commit messages are not allowed
   * - :ref:`CC009 <cc009>`
     - ``allow-fixup-commits``
     - Fixup commits are not allowed
   * - :ref:`CC010 <cc010>`
     - ``allow-wip-commits``
     - WIP commits are not allowed
   * - :ref:`CC011 <cc011>`
     - ``require-body``
     - Commit body is required
   * - :ref:`CC012 <cc012>`
     - ``require-signed-off-by``
     - Signed-off-by not found in latest commit
   * - :ref:`CC013 <cc013>`
     - ``ai-attribution``
     - AI attribution policy violation
   * - :ref:`CC101 <cc101>`
     - ``author-name``
     - The committer name seems invalid
   * - :ref:`CC102 <cc102>`
     - ``author-email``
     - The committer's email seems invalid
   * - :ref:`CC201 <cc201>`
     - ``branch``
     - The branch should follow Conventional Branch
   * - :ref:`CC202 <cc202>`
     - ``merge-base``
     - Current branch is not rebased onto target branch
   * - :ref:`CC301 <cc301>`
     - ``no-force-push``
     - Force push is not allowed

Commit message rules
--------------------

.. _cc001:

CC001 — message
~~~~~~~~~~~~~~~

**Config key:** ``message``

**Message:** The commit message should follow Conventional Commits. See https://www.conventionalcommits.org

**How to fix:** Use <type>(<scope>): <description> with allowed types

.. _cc002:

CC002 — subject-capitalized
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Config key:** ``subject_capitalized``

**Message:** Subject must start with a capital letter

**How to fix:** Capitalize the first word of the subject

.. _cc003:

CC003 — subject-imperative
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Config key:** ``subject_imperative``

**Message:** Commit message should use imperative mood (e.g., 'fix bug' not 'fixed bug', 'add feature' not 'adding feature')

**How to fix:** Change the first verb to imperative form, e.g., 'fix' instead of 'fixed'/'fixes'/'fixing'

.. _cc004:

CC004 — subject-max-length
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Config key:** ``subject_max_length``

**Message:** Subject must be at most {max_len} characters

**How to fix:** Keep the subject concise (<= configured max)

.. _cc005:

CC005 — subject-min-length
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Config key:** ``subject_min_length``

**Message:** Subject must be at least {min_len} characters

**How to fix:** Provide a meaningful subject (>= configured min)

.. _cc006:

CC006 — allow-merge-commits
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Config key:** ``allow_merge_commits``

**Message:** Merge commits are not allowed

**How to fix:** Rebase or squash your changes instead of merging

.. _cc007:

CC007 — allow-revert-commits
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Config key:** ``allow_revert_commits``

**Message:** Revert commits are not allowed

**How to fix:** Avoid using 'revert' commits; rewrite history if necessary

.. _cc008:

CC008 — allow-empty-commits
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Config key:** ``allow_empty_commits``

**Message:** Empty commit messages are not allowed

**How to fix:** Provide a non-empty subject

.. _cc009:

CC009 — allow-fixup-commits
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Config key:** ``allow_fixup_commits``

**Message:** Fixup commits are not allowed

**How to fix:** Use interactive rebase to clean up fixup commits

.. _cc010:

CC010 — allow-wip-commits
~~~~~~~~~~~~~~~~~~~~~~~~~

**Config key:** ``allow_wip_commits``

**Message:** WIP commits are not allowed

**How to fix:** Complete the work before committing or remove 'WIP'

.. _cc011:

CC011 — require-body
~~~~~~~~~~~~~~~~~~~~

**Config key:** ``require_body``

**Message:** Commit body is required

**How to fix:** Add a body explaining the change

.. _cc012:

CC012 — require-signed-off-by
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Config key:** ``require_signed_off_by``

**Message:** Signed-off-by not found in latest commit

**How to fix:** git commit --amend --signoff or use --signoff on commit

.. _cc013:

CC013 — ai-attribution
~~~~~~~~~~~~~~~~~~~~~~

**Config key:** ``ai_attribution``

**Message:** AI attribution policy violation

**How to fix:** This project forbids AI-assisted commits. Remove AI trailers and re-commit.

Author rules
------------

.. _cc101:

CC101 — author-name
~~~~~~~~~~~~~~~~~~~

**Config key:** ``author_name``

**Message:** The committer name seems invalid

**How to fix:** git config user.name 'Your Name'

.. _cc102:

CC102 — author-email
~~~~~~~~~~~~~~~~~~~~

**Config key:** ``author_email``

**Message:** The committer's email seems invalid

**How to fix:** git config user.email yourname@example.com

Branch rules
------------

.. _cc201:

CC201 — branch
~~~~~~~~~~~~~~

**Config key:** ``branch``

**Message:** The branch should follow Conventional Branch. See https://conventionalbranch.org

**How to fix:** Use <type>/<description> with allowed types or add branch name to allow_branch_names in config, or use ignore_authors in config branch section to bypass

.. _cc202:

CC202 — merge-base
~~~~~~~~~~~~~~~~~~

**Config key:** ``merge_base``

**Message:** Current branch is not rebased onto target branch

**How to fix:** Rebase or merge with the target branch

Push rules
----------

.. _cc301:

CC301 — no-force-push
~~~~~~~~~~~~~~~~~~~~~

**Config key:** ``no_force_push``

**Message:** Force push is not allowed

**How to fix:** Use a normal push instead of --force or --force-with-lease
