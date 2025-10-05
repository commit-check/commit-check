# pylint: disable=all
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import re
import datetime
from pathlib import Path
import subprocess
from sphinx.application import Sphinx

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
project = "commit-check"
copyright = f"{datetime.date.today().year}, shenxianpeng"
author = "shenxianpeng"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
extensions = [
    "sphinx_immaterial",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_issues",
]

autodoc_member_order = "bysource"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

default_role = "any"

# -- Options for sphinx_issues --------------------------------------------------------
issues_default_group_project = "commit-check/commit-check"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_immaterial"
html_static_path = ["_static"]
html_logo = "_static/logo.jpg"
# html_favicon = "_static/favicon.ico"
html_css_files = ["extra_css.css"]
html_title = "Commit Check"

html_theme_options = {
    "repo_url": "https://github.com/commit-check/commit-check",
    "repo_name": "commit-check",
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
    },
]
for name in ("hint", "tip", "important"):
    sphinx_immaterial_custom_admonitions.append(
        dict(name=name, icon="material/school", override=True)
    )


def setup(app: Sphinx):
    """Generate a doc from the executable script's ``--help`` output."""

    result = subprocess.run(
        ["commit-check", "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    doc = "commit-check --help\n==============================\n\n"
    CLI_OPT_NAME = re.compile(r"^\s*(\-\w)(?:\s+[A-Z_\[\]]*)?(?:,\s+(\-\-[a-z\-]+))?")
    in_options_section = False

    for line in result.stdout.splitlines():
        # Start processing options when we see the "options:" line
        if line.strip() == "options:":
            in_options_section = True
            doc += line + "\n"
            continue

        # Only process option patterns in the options section
        if in_options_section:
            match = CLI_OPT_NAME.search(line)
            if match is not None:
                short_opt = match.group(1)
                long_opt = match.group(2)
                if short_opt and long_opt:
                    doc += "\n.. std:option:: " + short_opt + ", " + long_opt + "\n\n"
                elif short_opt:
                    doc += "\n.. std:option:: " + short_opt + "\n\n"

        doc += line + "\n"
    cli_doc = Path(app.srcdir, "cli_args.rst")
    cli_doc.unlink(missing_ok=True)
    cli_doc.write_text(doc)
