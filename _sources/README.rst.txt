:orphan:

How to build the docs
=====================

From the root directory of the repository, do the following to steps

1. Install docs' dependencies

   .. code-block:: text

       pip install -r docs/requirements.txt

   On Linux, you may need to use ``pip3`` instead.

2. Build the docs

   .. code-block:: text

       sphinx-build docs docs/_build/html

   Browse the files in docs/_build/html with your internet browser to see the rendered
   output.
