"""The HTTPS-only opener that fetches a parent config for ``inherit_from``.

It lives apart from :mod:`commit_check.config` because ``urllib.request``
and ``urllib.error`` cost more to import than the rest of the CLI, and only
the rare run that inherits from a URL needs them.
"""

from __future__ import annotations

import urllib.error
import urllib.request


class HttpsOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow redirects only to HTTPS targets.

    ``urlopen`` follows an HTTPS-to-HTTP redirect by default, which would
    let a parent config be swapped in transit on the way to being merged
    into the policy. Any redirect off HTTPS is refused instead.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        if not newurl.startswith("https://"):
            raise urllib.error.URLError(
                f"redirect to a non-HTTPS URL refused: {newurl}"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_opener() -> urllib.request.OpenerDirector:
    """An opener that refuses any redirect off HTTPS."""
    return urllib.request.build_opener(HttpsOnlyRedirectHandler())
