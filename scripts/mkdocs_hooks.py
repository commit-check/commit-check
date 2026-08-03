"""MkDocs build hooks.

Two jobs:

* generate ``docs/cli.md`` from the CLI's own ``--help`` output, so the
  documented interface cannot drift from the shipped one;
* emit redirect stubs for the ``.html`` URLs the previous Sphinx site served,
  so links already published elsewhere keep working on hosts that have no
  other redirect mechanism (GitHub Pages). Netlify skips the stubs: it
  declares the same URLs as ``[[redirects]]`` in ``netlify.toml``, which
  resolve before file lookup and cannot collide with the pages they target.
"""

from __future__ import annotations

import os
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

# Redirect stubs for the URLs the Sphinx site served.
# The script carries the fragment across, because the links most worth keeping
# alive are the per-rule ones (``rules.html#cc003``) and a plain redirect drops
# the ``#cc003``. It also refuses to redirect a page to itself: a host that
# normalises ``/rules`` and ``/rules/`` to the same resource would otherwise
# serve this stub in place of the real page and loop forever.
REDIRECT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Redirecting…</title>
<link rel="canonical" href="{url}">
<script>
(function () {{
  var target = "{url}";
  var here = location.protocol + "//" + location.host + location.pathname;
  if (here !== target && here + "/" !== target) {{
    location.replace(target + location.hash);
  }}
}})();
</script>
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
    # On Netlify the stubs would be served in place of the real pages: Netlify
    # resolves ``/rules/`` to the file ``rules.html``, so the stub that
    # redirects to ``/rules/`` would shadow ``rules/index.html`` and loop. The
    # ``[[redirects]]`` table in netlify.toml covers the same URLs with real
    # 301s, so the stubs are only written for hosts without redirects.
    if os.environ.get("NETLIFY") == "true":
        return
    # Deploy previews pass their own URL in, and it may arrive without the
    # trailing slash the targets below are joined onto.
    base = (config["site_url"] or "/").rstrip("/") + "/"
    for legacy, target in LEGACY_URLS.items():
        (site / f"{legacy}.html").write_text(
            REDIRECT.format(url=base + target), encoding="utf-8"
        )
