Troubleshooting
===============

How to Skip Author Name Check
-----------------------------

In some cases, Commit Check may fail due to an invalid ``author_name``, as shown below:

.. code-block:: shell

    check committer name.....................................................Failed
    - hook id: check-author-name
    - exit code: 1

    Commit rejected by Commit-Check.                                  
                                                                                                                   
    Type author_name check failed => 12 
    It doesn't match regex: ^[A-Za-zÀ-ÖØ-öø-ÿ\u0100-\u017F\u0180-\u024F ,.\'-]+$|.*(\[bot])
    The committer name seems invalid
    Suggest: run command `git config user.name "Your Name"`

To fix it, you can either update your Git config or temporarily skip the check using one of the following methods.

Bypass Specific Hook
~~~~~~~~~~~~~~~~~~~~

Use the ``--no-verify`` flag to skip the pre-commit hook:

.. code-block:: shell

    # Amend the commit without running hooks
    git commit --amend --author="Xianpeng Shen <xianpeng.shen@gmail.com>" --no-edit --no-verify

Bypass All Hooks
----------------

Alternatively, use the ``SKIP=your-hook-name`` environment variable, like below:

.. code-block:: shell

    # Set the correct Git author name
    git config user.name "Xianpeng Shen"
    
    # Force amend while skipping the specified hook
    SKIP=check-author-name git commit --amend --author="Xianpeng Shen <xianpeng.shen@gmail.com>" --no-edit
