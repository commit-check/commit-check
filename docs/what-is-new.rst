What's New
==========

This document highlights the major changes and improvements in each version of commit-check.

Version 2.0.0 - Major Release
-----------------------------

Version 2.0.0 represents a complete architectural overhaul of commit-check, introducing significant improvements in configuration, usability, and maintainability.

**Overview**
~~~~~~~~~~~~~~~

The most significant change in v2.0.0 is the transition from YAML to TOML configuration format, along with a complete redesign of the validation engine using SOLID principles.

**Key Benefits:**

* **Simplified Configuration**: More intuitive TOML syntax
* **Better Defaults**: Sensible out-of-the-box behavior
* **Enhanced Validation**: Built-in support for Conventional Commits and Conventional Branches
* **Improved Architecture**: Modular, maintainable codebase
* **Better Documentation**: Comprehensive guides and examples

**Documentation & Migration**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Configuration Guide**: Updated `Configuration Documentation <configuration.html>`_ with comprehensive examples
* **Migration Support**: Complete `Migration Guide <migration.html>`_ for upgrading from v1.x to v2.0+

**Configuration Format Migration**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The configuration format has changed from YAML to TOML, providing better readability and easier maintenance.

**Format Comparison:**

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Feature
     - YAML (v1.x)
     - TOML (v2.0+)
   * - **Syntax**
     - Complex nested structure
     - Simple key-value pairs
   * - **Validation**
     - Custom regex patterns
     - Built-in conventional standards
   * - **Configuration**
     - ``.commit-check.yml``
     - ``cchk.toml`` or ``commit-check.toml``
   * - **Maintainability**
     - Manual regex maintenance
     - Standardized patterns


**Configuration Examples**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Below are side-by-side comparisons showing how common configurations translate from v1.x to v2.0+.

Commit Message Validation
^^^^^^^^^^^^^^^^^^^^^^^^^

Transform complex regex patterns into simple, standardized configuration.

**Before (YAML v1.x):**

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

**After (TOML v2.0+):**

.. code-block:: toml

    [commit]
    conventional_commits = true
    allow_commit_types = ["build", "chore", "ci", "docs", "feat", "fix", "perf", "refactor", "style", "test"]

**Benefits**: No more complex regex patterns, built-in `Conventional Commits <https://www.conventionalcommits.org/en/v1.0.0/>`_ support, clearer configuration.

Branch Naming Validation
^^^^^^^^^^^^^^^^^^^^^^^^

Standardize branch naming with conventional patterns.

**Before (YAML v1.x):**

.. code-block:: yaml

    checks:
      - check: branch
        regex: ^(bugfix|feature|release|hotfix|task|chore)\/.+|(master)|(main)|(HEAD)|(PR-.+)
        error: "Branches must begin with these types: bugfix/ feature/ release/ hotfix/ task/ chore/"
        suggest: run command `git checkout -b type/branch_name`

**After (TOML v2.0+):**

.. code-block:: toml

    [branch]
    conventional_branch = true
    allow_branch_types = ["bugfix", "feature", "release", "hotfix", "task", "chore"]

**Benefits**: Built-in `Conventional Branch <https://conventional-branch.github.io/>`_ support, automatic handling of special branches (main, master, HEAD, PR-\*).

Author Validation
^^^^^^^^^^^^^^^^^

Flexible author validation with allow/ignore lists.

**Before (YAML v1.x):**

.. code-block:: yaml

    checks:
      - check: author_name
        regex: ^[A-Za-zÀ-ÖØ-öø-ÿ\u0100-\u017F\u0180-\u024F ,.\'-]+$|.*(\[bot])
        error: The committer name seems invalid
        suggest: run command `git config user.name "Your Name"`

**After (TOML v2.0+):**

.. code-block:: toml

    [commit]
    # Built-in validation with sensible defaults for author name/email
    # Optional: restrict to specific authors
    allow_authors = ["John Doe <john@example.com>", "Jane Smith <jane@example.com>"]
    # Optional: ignore specific authors (e.g., bots)
    ignore_authors = ["dependabot[bot]", "renovate[bot]"]

**Benefits**: Built-in validation patterns, flexible allow/ignore lists, automatic bot detection.

Signed-off-by Requirements
^^^^^^^^^^^^^^^^^^^^^^^^^^

Simple boolean flag for DCO compliance.

**Before (YAML v1.x):**

.. code-block:: yaml

    checks:
      - check: commit_signoff
        regex: Signed-off-by:.*[A-Za-z0-9]\s+<.+@.+>
        error: Signed-off-by not found in latest commit
        suggest: run command `git commit -m "conventional commit message" --signoff`

**After (TOML v2.0+):**

.. code-block:: toml

    [commit]
    require_signed_off_by = true

**Benefits**: Simple boolean configuration, built-in DCO validation, clear error messages.

**Architecture Improvements**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**New Validation Engine**
^^^^^^^^^^^^^^^^^^^^^^^^^

* **SOLID Principles**: Maintainable, extensible design
* **Specialized Validators**: Dedicated classes for each validation type
* **Centralized Rules**: Rule catalog with consistent error messages
* **Flexible Configuration**: Dynamic rule building from configuration

**Module Organization**
^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Module
     - Purpose
   * - ``config.py``
     - TOML configuration loading and validation
   * - ``engine.py``
     - Core validation engine and specialized validators
   * - ``rule_builder.py``
     - Builds validation rules from configuration
   * - ``rules_catalog.py``
     - Centralized catalog of validation rules and messages
   * - ``main.py``
     - CLI interface and orchestration

**Getting Started with v2.0**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**For New Users:**
^^^^^^^^^^^^^^^^^^

1. **Install commit-check v2.0+**:

   .. code-block:: bash

       pip install commit-check>=2.0.0

2. **Start with defaults** (no configuration needed):

   .. code-block:: bash

       commit-check --message --branch

3. **Customize as needed** with ``cchk.toml``:

   .. code-block:: toml

       [commit]
       conventional_commits = true
       subject_max_length = 72

For Existing Users
^^^^^^^^^^^^^^^^^^^^^^
1. **Follow the Migration Guide**: See `Migration Guide <migration.html>`_
2. **Test thoroughly**: Validate your new configuration before deploying

**Additional Resources**
~~~~~~~~~~~~~~~~~~~~~~~~~~~

* `Configuration Reference <configuration.html>`_ - Complete configuration options
* `Migration Guide <migration.html>`_ - Step-by-step upgrade instructions
* `CLI Reference <cli_args.html>`_ - Command-line interface documentation
