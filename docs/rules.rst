Rules
=====

Every check that can report a failure has a **stable rule ID**. Rule IDs never
change once released, so they are safe to reference in commit messages, code
review comments, issue templates, and tooling.

Rule IDs appear in commit-check's output and in ``--format json`` results:

.. code-block:: text

    CC003 subject_imperative check failed ==> docs: revamped the profile
    Commit message should use imperative mood (e.g., 'fix bug' not 'fixed bug')
    Suggest: Change the first verb to imperative form, e.g., 'fix' instead of 'fixed'
    Docs: https://docs.commit-check.com/rules.html#cc003

``--compact`` prints one line per failure, keeping the rule ID and dropping the
explanation, suggestion, and documentation link:

.. code-block:: text

    [FAIL] CC003 subject_imperative: docs: revamped the profile

How to read this page
---------------------

Rule IDs are grouped by what they inspect:

.. list-table::
   :header-rows: 1
   :widths: 12 25 63

   * - Range
     - Category
     - Inspects
   * - ``CC0xx``
     - :ref:`Commit message <commit-message-rules>`
     - The subject, body, and trailers of a commit message
   * - ``CC1xx``
     - :ref:`Author <author-rules>`
     - The committer's configured name and email
   * - ``CC2xx``
     - :ref:`Branch <branch-rules>`
     - The current branch's name and its position relative to a target branch
   * - ``CC3xx``
     - :ref:`Push <push-rules>`
     - The push operation itself

Two things determine whether a rule runs:

**The check you select.** commit-check only evaluates the checks you ask for on
the command line. ``commit-check --message`` never reports a branch rule. The
*Check* column in the tables below shows which flag activates each rule.

**Its configuration.** Within a selected check, the *Default* column shows
whether the rule is active with no configuration at all:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Default
     - Meaning
   * - ✅ On
     - Enforced out of the box. Disable it through the listed option.
   * - ⚪ Off
     - Not enforced until you opt in through the listed option.

Rules that are off by default are not lesser rules — they encode conventions
that are right for some projects and wrong for others. Turning on
:ref:`CC002 <cc002>` makes sense for a project that capitalizes subjects, and is
actively harmful for one that does not.

.. tip::

    Every option named below is documented in full — with its type, default, and
    the matching environment variable and CLI flag — in
    :doc:`configuration`.

Rule index
----------

.. _commit-message-rules:

Commit message rules (``CC0xx``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run with ``-m`` / ``--message``.

.. list-table::
   :header-rows: 1
   :widths: 10 26 44 10 10
   :class: rules-index

   * - Code
     - Name
     - Message
     - Check
     - Default
   * - :ref:`CC001 <cc001>`
     - ``message``
     - The commit message should follow Conventional Commits
     - ``-m``
     - ✅ On
   * - :ref:`CC002 <cc002>`
     - ``subject-capitalized``
     - Subject must start with a capital letter
     - ``-m``
     - ⚪ Off
   * - :ref:`CC003 <cc003>`
     - ``subject-imperative``
     - Commit message should use imperative mood
     - ``-m``
     - ⚪ Off
   * - :ref:`CC004 <cc004>`
     - ``subject-max-length``
     - Subject must be at most ``{max_len}`` characters
     - ``-m``
     - ✅ On
   * - :ref:`CC005 <cc005>`
     - ``subject-min-length``
     - Subject must be at least ``{min_len}`` characters
     - ``-m``
     - ✅ On
   * - :ref:`CC006 <cc006>`
     - ``allow-merge-commits``
     - Merge commits are not allowed
     - ``-m``
     - ⚪ Off
   * - :ref:`CC007 <cc007>`
     - ``allow-revert-commits``
     - Revert commits are not allowed
     - ``-m``
     - ⚪ Off
   * - :ref:`CC008 <cc008>`
     - ``allow-empty-commits``
     - Empty commit messages are not allowed
     - ``-m``
     - ⚪ Off
   * - :ref:`CC009 <cc009>`
     - ``allow-fixup-commits``
     - Fixup commits are not allowed
     - ``-m``
     - ⚪ Off
   * - :ref:`CC010 <cc010>`
     - ``allow-wip-commits``
     - WIP commits are not allowed
     - ``-m``
     - ⚪ Off
   * - :ref:`CC011 <cc011>`
     - ``require-body``
     - Commit body is required
     - ``-m``
     - ⚪ Off
   * - :ref:`CC012 <cc012>`
     - ``require-signed-off-by``
     - Signed-off-by not found in latest commit
     - ``-m``
     - ⚪ Off
   * - :ref:`CC013 <cc013>`
     - ``ai-attribution``
     - AI attribution policy violation
     - ``-m``
     - ⚪ Off

.. _author-rules:

Author rules (``CC1xx``)
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 26 44 10 10
   :class: rules-index

   * - Code
     - Name
     - Message
     - Check
     - Default
   * - :ref:`CC101 <cc101>`
     - ``author-name``
     - The committer name seems invalid
     - ``-n``
     - ✅ On
   * - :ref:`CC102 <cc102>`
     - ``author-email``
     - The committer's email seems invalid
     - ``-e``
     - ✅ On

.. _branch-rules:

Branch rules (``CC2xx``)
~~~~~~~~~~~~~~~~~~~~~~~~

Run with ``-b`` / ``--branch``.

.. list-table::
   :header-rows: 1
   :widths: 10 26 44 10 10
   :class: rules-index

   * - Code
     - Name
     - Message
     - Check
     - Default
   * - :ref:`CC201 <cc201>`
     - ``branch``
     - The branch should follow Conventional Branch
     - ``-b``
     - ✅ On
   * - :ref:`CC202 <cc202>`
     - ``merge-base``
     - Current branch is not rebased onto target branch
     - ``-b``
     - ⚪ Off

.. _push-rules:

Push rules (``CC3xx``)
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 10 26 44 10 10
   :class: rules-index

   * - Code
     - Name
     - Message
     - Check
     - Default
   * - :ref:`CC301 <cc301>`
     - ``no-force-push``
     - Force push is not allowed
     - ``--no-force-push``
     - ⚪ Off

Commit message rules
--------------------

.. _cc001:

message (CC001)
~~~~~~~~~~~~~~~

**What it does**

Checks that the commit message subject follows the
`Conventional Commits <https://www.conventionalcommits.org>`_ specification:
``<type>(<scope>)!: <description>``.

**Why is this bad?**

A free-form subject can only be read by a human. A structured one can be read by
tooling: release-drafting can group changes by type, semantic versioning can
infer whether a release is a patch, minor, or major, and ``git log`` becomes
filterable by area of the codebase. Once a fraction of the history is
unstructured, every consumer of that history needs a fallback path.

**Example**

.. code-block:: text

    updated the parser

Use instead:

.. code-block:: text

    fix(parser): handle empty input

**Options**

* ``commit.conventional_commits`` — set to ``false`` to disable this rule.
* ``commit.allow_commit_types`` — the accepted ``<type>`` values.
* ``commit.message_pattern`` — a custom regex that replaces the generated
  Conventional Commits pattern entirely, for formats such as JIRA smart commits
  (``"^PROJ-\\d+: .+"``).

.. _cc002:

subject-capitalized (CC002)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**What it does**

Checks that the description in the subject line starts with a capital letter.

**Why is this bad?**

Nothing is inherently wrong with either casing — but mixing them is. A history
where half the subjects read ``fix: handle empty input`` and the other half read
``fix: Handle empty input`` looks careless in ``git log --oneline``, and gives
reviewers a pointless thing to comment on. This rule picks the capitalized
convention and enforces it.

Leave it off if your project deliberately uses lowercase descriptions, which is
the more common convention among projects that follow Conventional Commits.

**Example**

.. code-block:: text

    fix: handle empty input

Use instead:

.. code-block:: text

    fix: Handle empty input

**Options**

* ``commit.subject_capitalized`` — set to ``true`` to enable this rule.

.. _cc003:

subject-imperative (CC003)
~~~~~~~~~~~~~~~~~~~~~~~~~~

**What it does**

Checks that the first word of the description is in the imperative mood —
``fix``, not ``fixed``, ``fixes``, or ``fixing``.

**Why is this bad?**

This is Git's own convention: a subject should complete the sentence *"If
applied, this commit will ___"*. ``If applied, this commit will fixed a crash``
does not read as English. Beyond grammar, the imperative form is the shortest of
the three, which matters on a line that tooling truncates around 50 characters.

**Example**

.. code-block:: text

    fix: fixed a crash when the config file is empty

Use instead:

.. code-block:: text

    fix: handle an empty config file

**Options**

* ``commit.subject_imperative`` — set to ``true`` to enable this rule.

The list of recognised non-imperative verb forms lives in
`imperatives.py <https://github.com/commit-check/commit-check/blob/main/commit_check/imperatives.py>`_.

.. _cc004:

subject-max-length (CC004)
~~~~~~~~~~~~~~~~~~~~~~~~~~

**What it does**

Checks that the subject line is at most a configured number of characters.

**Why is this bad?**

Long subjects get truncated by the tools that display them —
``git log --oneline``, ``git shortlog``, GitHub's commit list, and most Git
GUIs all cut off somewhere between 50 and 72 columns. A subject that carries its
meaning past that point loses it exactly where people skim. Detail belongs in
the body, which nothing truncates.

**Example**

.. code-block:: text

    fix: handle an empty config file and also fix the unrelated crash in the branch parser that happens on Windows

Use instead:

.. code-block:: text

    fix: handle an empty config file

    Also fixes the branch parser crash on Windows, which shared the
    same root cause.

**Options**

* ``commit.subject_max_length`` — the limit, in characters. Defaults to ``80``.
  ``50`` and ``72`` are the other conventional choices.

.. _cc005:

subject-min-length (CC005)
~~~~~~~~~~~~~~~~~~~~~~~~~~

**What it does**

Checks that the subject line is at least a configured number of characters.

**Why is this bad?**

Subjects like ``fix``, ``wip``, or ``.`` describe nothing. They are invisible in
a blame view and useless in a bisect session, and they are almost always the
result of a hurried commit rather than a deliberate one.

**Example**

.. code-block:: text

    fix: bug

Use instead:

.. code-block:: text

    fix: reject config files with a null inherit_from

**Options**

* ``commit.subject_min_length`` — the minimum, in characters. Defaults to ``5``.

.. _cc006:

allow-merge-commits (CC006)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**What it does**

Rejects merge commits — the ``Merge branch '...'`` commits that ``git pull``
creates.

**Why is this bad?**

Merge commits created by ``git pull`` carry no information: they record that
someone synced, not that anything was decided. On a busy repository they can
outnumber real commits, which makes ``git log`` unreadable, adds branches for
``git bisect`` to walk, and breaks the assumption behind
``git log --first-parent``. Projects that want a linear history rebase instead.

**Example**

.. code-block:: bash

    git pull

Use instead:

.. code-block:: bash

    git pull --rebase

    # or make it the default
    git config --global pull.rebase true

**Options**

* ``commit.allow_merge_commits`` — set to ``false`` to enable this rule.

.. _cc007:

allow-revert-commits (CC007)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**What it does**

Rejects the ``Revert "..."`` commits that ``git revert`` generates.

**Why is this bad?**

A generated revert subject describes the mechanics of the change and nothing
about the reason for it. Six months later, ``Revert "feat: add caching layer"``
answers "what happened" but not the only question that matters: why the feature
was backed out, and whether it is safe to try again.

**Example**

.. code-block:: text

    Revert "feat: add caching layer"

Use instead:

.. code-block:: text

    fix: remove the caching layer

    The cache served stale permissions after a role change (#412).
    Reverts 4a1c9f2; re-land once invalidation is keyed on role version.

**Options**

* ``commit.allow_revert_commits`` — set to ``false`` to enable this rule.

.. _cc008:

allow-empty-commits (CC008)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**What it does**

Rejects commits with an empty message.

**Why is this bad?**

A commit with no subject cannot be searched for, summarised, or reviewed. It is
a gap in the history that nobody can fill in later.

**Options**

* ``commit.allow_empty_commits`` — set to ``false`` to enable this rule.

.. _cc009:

allow-fixup-commits (CC009)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**What it does**

Rejects ``fixup!`` and ``squash!`` commits.

**Why is this bad?**

These commits exist to be consumed by ``git rebase --autosquash`` before a
branch is merged. One that survives to the target branch means the autosquash
was forgotten — leaving behind a commit that, by construction, does not stand on
its own.

**Example**

.. code-block:: text

    fixup! feat: add the caching layer

Use instead:

.. code-block:: bash

    git rebase -i --autosquash main

**Options**

* ``commit.allow_fixup_commits`` — set to ``false`` to enable this rule.

.. _cc010:

allow-wip-commits (CC010)
~~~~~~~~~~~~~~~~~~~~~~~~~

**What it does**

Rejects work-in-progress commits — subjects beginning with ``WIP``.

**Why is this bad?**

A WIP commit is an explicit statement that the change is not finished. That is
useful on a local branch and wrong on a shared one, where every commit is
something another developer may bisect through or build on.

**Example**

.. code-block:: text

    WIP: caching

Use instead:

.. code-block:: bash

    # keep the work, drop the marker
    git commit --amend -m "feat: add a caching layer for role lookups"

**Options**

* ``commit.allow_wip_commits`` — set to ``false`` to enable this rule.

.. _cc011:

require-body (CC011)
~~~~~~~~~~~~~~~~~~~~

**What it does**

Requires a non-empty body after the subject line.

**Why is this bad?**

The subject says *what* changed; the diff already says that too. The body says
*why* — the constraint, the bug report, the rejected alternative. That reasoning
is the one thing that cannot be recovered from the code later, and it is exactly
what the next person to touch the change needs.

**Example**

.. code-block:: text

    fix: cap the retry backoff at 30s

Use instead:

.. code-block:: text

    fix: cap the retry backoff at 30s

    The unbounded exponential backoff reached 45 minutes during the
    incident on 2026-05-11, long after the upstream had recovered.

**Options**

* ``commit.require_body`` — set to ``true`` to enable this rule.

.. _cc012:

require-signed-off-by (CC012)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**What it does**

Requires a ``Signed-off-by:`` trailer in the commit message.

**Why is this bad?**

Projects that use the `Developer Certificate of Origin
<https://developercertificate.org/>`_ — the Linux kernel, and much of the
CNCF — treat that trailer as the contributor's statement that they have the
right to submit the code. A commit without it cannot be merged, so catching it
locally saves a round trip through CI.

**Example**

.. code-block:: bash

    git commit -m "fix: handle an empty config file"

Use instead:

.. code-block:: bash

    git commit --signoff -m "fix: handle an empty config file"

    # or fix the commit you already made
    git commit --amend --signoff

**Options**

* ``commit.require_signed_off_by`` — set to ``true`` to enable this rule.

.. _cc013:

ai-attribution (CC013)
~~~~~~~~~~~~~~~~~~~~~~

**What it does**

Rejects commits carrying the signatures that AI coding tools add to commit
messages — trailers naming Claude Code, Copilot, Codex, Gemini, Cursor, Devin,
Aider, Windsurf, Tabby, and generic AI model patterns.

**Why is this bad?**

Whether AI-assisted commits are acceptable is a policy question, and projects
have landed on different answers: the Linux kernel added an ``Assisted-by:``
trailer, while others disallow the practice outright. This rule exists for
projects that have made that decision and want it enforced mechanically rather
than relitigated in every code review.

It is off by default, and the default policy is ``"ignore"``. Enable it only if
your project has a stated position.

**Options**

* ``commit.ai_attribution`` — ``"forbid"`` enables this rule, ``"ignore"``
  (the default) disables it.

Author rules
------------

.. _cc101:

author-name (CC101)
~~~~~~~~~~~~~~~~~~~

**What it does**

Checks the committer's configured name against a pattern. The built-in pattern
accepts letters (including accented Latin characters), spaces, and
``, . ' -``, and always allows ``[bot]`` accounts.

**Why is this bad?**

When ``user.name`` is unset, Git falls back to the machine's account name.
Histories built in CI containers and on fresh VMs fill up with commits by
machine accounts — authorship that cannot be traced back to a person, which
matters for both code archaeology and compliance.

**Example**

.. code-block:: bash

    git config user.name ec2-user

Use instead:

.. code-block:: bash

    git config --global user.name "Your Name"

**Options**

* ``commit.author_name_pattern`` — a custom regex replacing the built-in
  pattern. For example, ``"^.+ .+$"`` to require a full name.

.. note::

    The built-in pattern accepts any name made of letters, spaces, and
    ``, . ' -``, so plain account names such as ``root`` or ``ubuntu`` still
    pass it — only names containing digits or other symbols are rejected. Set
    ``author_name_pattern`` if you need something stricter.

.. _cc102:

author-email (CC102)
~~~~~~~~~~~~~~~~~~~~

**What it does**

Checks the committer's configured email against a pattern. The built-in pattern
is ``^.+@.+$``, which only requires an ``@`` with something on either side.

**Why is this bad?**

An address with no ``@`` is not routable, so it breaks the link between a commit
and its author: forges cannot attribute the commit to an account, and
mailmap-based tooling cannot merge identities.

The built-in pattern is deliberately permissive — it is a sanity check, not a
policy. Its real value comes from replacing it, which is how organisations
require contributions to come from a corporate address.

**Example**

With ``author_email_pattern = "^.+@example\\.com$"`` configured:

.. code-block:: bash

    git config user.email you@gmail.com

Use instead:

.. code-block:: bash

    git config --global user.email you@example.com

**Options**

* ``commit.author_email_pattern`` — the regex to match against. Defaults to
  ``^.+@.+$``; set something like ``"^.+@example\\.com$"`` to require a company
  domain.

.. note::

    Because the built-in pattern only looks for an ``@``, local and placeholder
    addresses such as ``root@localhost`` pass it. Set ``author_email_pattern``
    if you need to reject those.

Branch rules
------------

.. _cc201:

branch (CC201)
~~~~~~~~~~~~~~

**What it does**

Checks that the current branch name follows the
`Conventional Branch <https://conventionalbranch.org/>`_ specification:
``<type>/<description>``.

``master``, ``main``, ``HEAD``, and ``PR-*`` are always accepted.

**Why is this bad?**

A predictable prefix is something automation can act on: CI can skip expensive
jobs for ``docs/`` branches, deployment workflows can key off ``release/``, and
branch protection rules can be written per type. It also makes a list of a
hundred open branches scannable, which an unstructured list never is.

**Example**

.. code-block:: text

    my-fix
    johns-branch-2

Use instead:

.. code-block:: text

    fix/empty-config-crash
    feature/role-caching

**Options**

* ``branch.conventional_branch`` — set to ``false`` to disable this rule.
* ``branch.allow_branch_types`` — the accepted ``<type>`` values. The default is
  a superset of the specification: the spec types plus the Conventional Commit
  types, AI agent prefixes (``ai``, ``claude``, ``codex``, ``copilot``,
  ``cursor``), and bot prefixes (``dependabot``, ``renovate``). Set it
  explicitly for strict spec-only validation.
* ``branch.allow_branch_names`` — additional standalone names to accept, such as
  ``["develop", "staging"]``.
* ``branch.ignore_authors`` — bypass the check for specific authors.

.. _cc202:

merge-base (CC202)
~~~~~~~~~~~~~~~~~~

**What it does**

Checks that the current branch is rebased onto a target branch.

**Why is this bad?**

A branch that has fallen behind is tested against code that no longer exists on
the target. CI passing on it says little about whether it will pass after
merging, and the failures it hides — a renamed function, a changed migration —
surface on the target branch instead of the pull request.

**Example**

.. code-block:: bash

    # branch was cut from main three weeks ago
    git push

Use instead:

.. code-block:: bash

    git fetch origin
    git rebase origin/main
    git push --force-with-lease

**Options**

* ``branch.require_rebase_target`` — the target branch, for example ``"main"``.
  Unset by default, meaning no rebase requirement.

Push rules
----------

.. _cc301:

no-force-push (CC301)
~~~~~~~~~~~~~~~~~~~~~

**What it does**

Blocks force pushes. Run it as a ``pre-push`` hook, where it reads the push
details from stdin, or with ``--no-force-push``, where it compares the current
branch against its upstream.

**Why is this bad?**

A force push to a shared branch rewrites history that other people have already
based work on. Their next pull produces conflicts against commits that no longer
exist, and any commit pushed between their fetch and the force push is silently
dropped. On a personal branch this is a routine part of rebasing; on a shared
one it is a data-loss event.

**Example**

.. code-block:: bash

    git push --force

Use instead:

.. code-block:: bash

    # on a shared branch, add a commit rather than rewriting
    git revert <sha>

    # on your own branch, at least refuse to clobber someone else's work
    git push --force-with-lease

**Options**

* ``push.allow_force_push`` — set to ``false`` to enable this rule.
