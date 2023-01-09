# pylint: disable=all
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import re
from pathlib import Path
import io
from sphinx.application import Sphinx
from commit_check.main import get_parser

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
project = "commit-check"
copyright = "2023, shenxianpeng"
author = "shenxianpeng"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
extensions = [
    "sphinx_immaterial",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
}

autodoc_member_order = "bysource"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

default_role = "any"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_immaterial"
html_static_path = ["_static"]
html_logo = "_static/logo.jpg"
# html_favicon = "_static/favicon.ico"
html_css_files = ["extra_css.css"]
html_title = "commit-check"

html_theme_options = {
    "repo_url": "https://github.com/commit-check/commit-check",
    "repo_name": "commit-check",
    "repo_type": "github",
    "palette": [
        {
            "media": "(prefers-color-scheme: light)",
            "scheme": "default",
            "primary": "light-blue",
            "accent": "deep-purple",
            "toggle": {
                "icon": "material/lightbulb-outline",
                "name": "Switch to dark mode",
            },
        },
        {
            "media": "(prefers-color-scheme: dark)",
            "scheme": "slate",
            "primary": "light-blue",
            "accent": "deep-purple",
            "toggle": {
                "icon": "material/lightbulb",
                "name": "Switch to light mode",
            },
        },
    ],
    "features": [
        "navigation.top",
        "navigation.tabs",
        "navigation.tabs.sticky",
        "toc.sticky",
        "toc.follow",
        "search.share",
    ],
}

object_description_options = [
    ("py:parameter", dict(include_in_toc=False)),
]

sphinx_immaterial_custom_admonitions = [
    {
        "name": "seealso",
        "color": (215, 59, 205),
        "icon": "octicons/eye-24",
        "override": True,
    },
    {
        "name": "note",
        "icon": "material/file-document-edit-outline",
        "override": True,
    }
]
for name in ("hint", "tip", "important"):
    sphinx_immaterial_custom_admonitions.append(
        dict(name=name, icon="material/school", override=True)
    )


def setup(app: Sphinx):
    """Generate a doc from the executable script's ``--help`` output."""

    with io.StringIO() as help_out:
        parser = get_parser()
        parser.print_help(help_out)
        output = help_out.getvalue()
    doc = "commit-check --help\n==============================\n\n"
    CLI_OPT_NAME = re.compile(r"^\s*(\-\w)\s?[A-Z_]*,\s(\-\-.*?)\s")
    for line in output.splitlines():
        match = CLI_OPT_NAME.search(line)
        if match is not None:
            # print(match.groups())
            doc += "\n.. std:option:: " + ", ".join(match.groups()) + "\n\n"
        doc += line + "\n"
    cli_doc = Path(app.srcdir, "cli_args.rst")
    cli_doc.unlink(missing_ok=True)
    cli_doc.write_text(doc)
