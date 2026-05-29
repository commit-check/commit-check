Policy Presets & Adoption Kit
============================

**Don't guess. Pick a preset.**

Commit Check exposes over 20 configuration options. Instead of wading through
every toggle, start with one of three presets designed for different use cases.
Each preset is a ready-to-use ``cchk.toml`` fragment that you can inherit with
a single line.  You can always add local overrides on top.

.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none


Choose Your Preset
------------------

.. list-table::
   :header-rows: 1
   :widths: 25 25 25 25

   * - Use case
     - Preset
     - What it enforces
     - One-liner
   * - | 🧑‍💻 **Personal / solo project**
       | You work alone, want basic consistency
       | without slowing you down.
     - **Minimal**
     - | ✅ Conventional Commits
       | ✅ Conventional Branch
       | ❌ Everything else relaxed
     - .. code-block:: toml

          inherit_from = "github:commit-check/commit-check:presets/minimal.toml"
   * - | 📦 **Open source project**
       | You maintain a library or tool with
       | external contributors. Want review-friendly
       | history without over-engineering.
     - **Recommended**
     - | ✅ Conventional Commits
       | ✅ Imperative mood
       | ✅ Subject length limits
       | ✅ Conventional Branch
       | ✅ Blocks force pushes
       | ✅ Blocks WIP commits
       | ❌ Capitalization not required
       | ❌ No sign-off required
     - .. code-block:: toml

          inherit_from = "github:commit-check/commit-check:presets/recommended.toml"
   * - | 🏢 **Enterprise / regulated**
       | You work in a team that demands
       | full traceability, sign-off, and
       | clean audit trails.
     - **Strict**
     - | ✅ Conventional Commits
       | ✅ Imperative mood
       | ✅ Capitalized subjects
       | ✅ Subject length (10–72)
       | ✅ Conventional Branch
       | ✅ Blocks force pushes
       | ✅ Blocks WIP / empty / fixup
       | ✅ Requires commit body
       | ✅ Requires Signed-off-by
       | ✅ Requires rebase onto main
     - .. code-block:: toml

          inherit_from = "github:commit-check/commit-check:presets/strict.toml"


Quick Start: 30 Seconds to Configure
-------------------------------------

**Step 1 — Pick your preset:**

+---------------------------+-----------------------------------------------+
| Your situation            | Use this                                      |
+===========================+===============================================+
| I work alone              | ``presets/minimal.toml``                      |
+---------------------------+-----------------------------------------------+
| I run an open source repo | ``presets/recommended.toml``                  |
+---------------------------+-----------------------------------------------+
| I work in a company team  | ``presets/strict.toml``                       |
+---------------------------+-----------------------------------------------+

**Step 2 — Create your config file** (choose one location):

.. code-block:: toml
   :caption: .github/cchk.toml  (recommended — keeps root clean)

   inherit_from = "github:commit-check/commit-check:presets/recommended.toml"

   # Optional: add local overrides below
   [commit]
   subject_max_length = 72

.. code-block:: toml
   :caption: cchk.toml  (root directory)

   inherit_from = "github:commit-check/commit-check:presets/recommended.toml"

**Step 3 — Done.**  ``commit-check`` picks up the preset automatically.  No
need to copy-paste 20 options.

You can also pin to a specific version tag for stability:

.. code-block:: toml

   inherit_from = "github:commit-check/commit-check@v2.6.0:presets/recommended.toml"


What Each Preset Checks (Side-by-Side)
--------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 15 17 17 26

   * - Check
     - Minimal
     - Recommended
     - Strict
     - Notes
   * - Conventional Commits
     - ✅
     - ✅
     - ✅
     - All presets require ``type(scope): description``
   * - Subject capitalized
     - ❌
     - ❌
     - ✅
     - ``Feat: ...`` (capital F)
   * - Subject imperative
     - ❌
     - ✅
     - ✅
     - ``fix`` not ``fixed``
   * - Max subject length
     - ❌
     - 80
     - 72
     - Characters (GitHub truncates at 72 in log)
   * - Min subject length
     - ❌
     - 5
     - 10
     - Characters
   * - Allowed commit types
     - 10 types
     - 10 types
     - 10 types
     - feat, fix, docs, style, refactor, test, chore, perf, build, ci
   * - Merge commits
     - ✅ allowed
     - ✅ allowed
     - ✅ allowed
     -
   * - Revert commits
     - ✅ allowed
     - ✅ allowed
     - ✅ allowed
     -
   * - Empty commits
     - ✅ allowed
     - ❌ blocked
     - ❌ blocked
     -
   * - Fixup commits
     - ✅ allowed
     - ✅ allowed
     - ❌ blocked
     - ``fixup! ...`` / ``squash! ...``
   * - WIP commits
     - ✅ allowed
     - ❌ blocked
     - ❌ blocked
     - ``WIP: ...`` / ``wip: ...``
   * - Require body
     - ❌
     - ❌
     - ✅
     -
   * - Require Signed-off-by
     - ❌
     - ❌
     - ✅
     - DCO-style sign-off
   * - Conventional Branch
     - ✅
     - ✅
     - ✅
     - ``<type>/<description>``
   * - Allowed branch types
     - 7 types
     - 7 types
     - 5 types
     - Strict removes ``feat``, ``fix``
   * - Require rebase
     - ❌
     - ❌
     - ✅ onto main
     - Branch must be rebased onto ``main``
   * - Block force push
     - ❌
     - ✅
     - ✅
     - ``git push --force`` rejected


Overriding and Extending Presets
--------------------------------

Presets use ``inherit_from``, so you can override any option in your local
config file.  Local settings always take priority:

.. code-block:: toml
   :caption: .github/cchk.toml

   inherit_from = "github:commit-check/commit-check:presets/recommended.toml"

   [commit]
   # Override: our team prefers capitalized subjects
   subject_capitalized = true
   # Override: allow additional commit types used by our tooling
   allow_commit_types = ["feat", "fix", "docs", "style", "refactor", "test", "chore", "perf", "build", "ci", "infra", "deps"]

   [branch]
   # Override: add custom branch names
   allow_branch_names = ["develop", "staging"]


Using a Local Copy (Air-Gapped / Offline)
-----------------------------------------

If you prefer not to fetch from GitHub at runtime, copy the preset file
directly into your repository and use a local path:

.. code-block:: bash

   # Download the preset once
   curl -o .github/cchk.toml \
     https://raw.githubusercontent.com/commit-check/commit-check/main/presets/recommended.toml

Then edit ``.github/cchk.toml`` directly to add overrides (no ``inherit_from``
needed — you're editing the file itself).

Alternatively, point ``inherit_from`` at a local relative path:

.. code-block:: toml

   inherit_from = "../shared-org-config/presets/strict.toml"


FAQ
---

**Q: Can I switch presets later?**

Yes. Just change the ``inherit_from`` line.  Existing commit history is
unaffected — only future commits are validated.

**Q: What if I need a mix of Recommended and Strict?**

Start with ``recommended.toml`` and add the Strict options you want as local
overrides (e.g., ``require_signed_off_by = true``).  You don't need to pick
one preset exactly.

**Q: Do presets work in CI / pre-commit / GitHub Actions?**

Yes. All enforcement points read the same ``cchk.toml``, so the preset applies
everywhere automatically.

**Q: Are presets versioned?**

Yes — pin to a tag for stability:

.. code-block:: toml

   inherit_from = "github:commit-check/commit-check@v2.6.0:presets/recommended.toml"

**Q: What happens to my old custom config?**

Nothing breaks.  Presets are opt-in.  If you already have a ``cchk.toml``
without ``inherit_from``, it keeps working as before.
