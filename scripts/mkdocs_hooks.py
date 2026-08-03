"""MkDocs build hooks.

Two jobs:

* generate ``docs/cli.md`` from the CLI's own ``--help`` output, so the
  documented interface cannot drift from the shipped one;
* emit redirects for the ``.html`` URLs the previous Sphinx site served, so
  links already published elsewhere keep working.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

#: Sphinx page name -> path under the MkDocs site.
LEGACY_URLS = {
    "configuration": "configuration/",
    "rules": "rules/",
    "example": "example/",
    "migration": "migration/",
    "troubleshoot": "troubleshoot/",
    "changelog": "changelog/",
    "what-is-new": "what-is-new/",
    "cli_args": "cli/",
    "README": "getting-started/installation/",
    "genindex": "",
}

REDIRECT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Redirecting…</title>
<link rel="canonical" href="{url}">
<meta http-equiv="refresh" content="0; url={url}">
</head>
<body>Redirecting to <a href="{url}">{url}</a>…</body>
</html>
"""

PAGE = """# CLI reference

Generated from `commit-check --help`. The CLI is also available as `cchk`.

```console
$ commit-check --help
```

```text
{help}
```

## See also

- [Configuration](configuration.md) — every option, with the environment
  variable and TOML key that set it.
- [Rules](rules.md) — which flag activates which rule.
"""


def on_pre_build(config, **kwargs) -> None:
    """Write ``cli.md`` before the build reads the docs directory."""
    try:
        result = subprocess.run(
            ["commit-check", "--help"],
            capture_output=True,
            encoding="utf-8",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover
        raise RuntimeError(
            "could not run 'commit-check --help' to generate the CLI reference; "
            "install the package first (pip install -e .)"
        ) from exc

    text = result.stdout.rstrip()
    target = Path(config["docs_dir"], "cli.md")
    target.write_text(PAGE.format(help=text), encoding="utf-8")


def on_post_build(config, **kwargs) -> None:
    """Write a redirect stub for each URL the Sphinx site used to serve."""
    site = Path(config["site_dir"])
    # Deploy previews pass their own URL in, and it may arrive without the
    # trailing slash the targets below are joined onto.
    base = (config["site_url"] or "/").rstrip("/") + "/"
    for legacy, target in LEGACY_URLS.items():
        (site / f"{legacy}.html").write_text(
            REDIRECT.format(url=base + target), encoding="utf-8"
        )
