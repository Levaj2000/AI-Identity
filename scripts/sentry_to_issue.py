"""Mirror recent unresolved Sentry errors to public GitHub issues without event data."""

import json
import os
import re
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

SENTRY_API = "https://sentry.io/api/0"
GITHUB_API = "https://api.github.com"
SLUG = re.compile(r"[a-zA-Z0-9_-]+")
ISSUE_ID = re.compile(r"[0-9]+")
MARKER = re.compile(r"<!-- sentry-issue:([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/[0-9]+) -->")
WINDOW = timedelta(days=14)
MAX_NEW_ISSUES = 10


def request_json(url, token, *, method="GET", data=None):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(
        url,
        headers=headers,
        data=json.dumps(data).encode("utf-8") if data is not None else None,
        method=method,
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response), response.headers.get("Link", "")
    except (HTTPError, URLError) as exc:
        # Do not print response bodies: they can include private Sentry data.
        raise RuntimeError(f"{method} {urlsplit(url).path} failed: {exc}") from None


def next_page(link, current_url):
    """Accept a next link only from the same HTTPS API endpoint."""
    for part in link.split(","):
        match = re.match(r'\s*<([^>]+)>;\s*rel="next"(.*)', part)
        if not match or 'results="false"' in match.group(2):
            continue
        candidate = match.group(1)
        old, new = urlsplit(current_url), urlsplit(candidate)
        if (new.scheme, new.netloc, new.path) != ("https", old.netloc, old.path):
            raise ValueError("Unexpected pagination URL")
        return candidate
    return None


def pages(url, token):
    visited = set()
    while url:
        if url in visited:
            raise ValueError("Pagination loop")
        visited.add(url)
        items, link = request_json(url, token)
        if not isinstance(items, list):
            raise ValueError("Expected an API list")
        yield from items
        url = next_page(link, url)


def issue_key(org, project, issue_id):
    if not ISSUE_ID.fullmatch(str(issue_id)):
        raise ValueError("Invalid Sentry issue ID")
    return f"{org}/{project}/{issue_id}"


def new_issue(org, project, issue_id):
    key = issue_key(org, project, issue_id)
    return {
        "title": f"Investigate Sentry error {project} #{issue_id}",
        "body": (
            f"<!-- sentry-issue:{key} -->\n"
            f"Review the error in Sentry: https://{org}.sentry.io/issues/{issue_id}/\n\n"
            "The details stay in Sentry to avoid exposing event data in this public repository."
        ),
    }


def recent_errors(issues, now):
    cutoff = now - WINDOW
    for issue in issues:
        if issue.get("status") != "unresolved" or issue.get("level") not in ("error", "fatal"):
            continue
        last_seen = datetime.fromisoformat(issue["lastSeen"].replace("Z", "+00:00"))
        if last_seen >= cutoff:
            yield issue


def sync(org, project, sentry_token, github_token, repository, now=None):
    if not all(SLUG.fullmatch(value) for value in (org, project)):
        raise ValueError("SENTRY_ORG and SENTRY_PROJECT must be slugs")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", repository):
        raise ValueError("GH_REPOSITORY must be owner/repo")
    now = now or datetime.now(UTC)

    github_url = f"{GITHUB_API}/repos/{repository}/issues"
    existing = set()
    for issue in pages(
        f"{github_url}?{urlencode({'state': 'all', 'per_page': 100})}", github_token
    ):
        if "pull_request" not in issue:
            existing.update(MARKER.findall(issue.get("body") or ""))

    sentry_url = (
        f"{SENTRY_API}/projects/{org}/{project}/issues/"
        f"?{urlencode({'query': 'is:unresolved', 'per_page': 100})}"
    )
    created = 0
    for issue in recent_errors(pages(sentry_url, sentry_token), now):
        key = issue_key(org, project, issue["id"])
        if key in existing:
            continue
        if created >= MAX_NEW_ISSUES:
            break
        request_json(
            github_url, github_token, method="POST", data=new_issue(org, project, issue["id"])
        )
        existing.add(key)
        created += 1
    print(f"Created {created} GitHub issues for recent Sentry errors")
    return created


if __name__ == "__main__":
    required = ("SENTRY_ORG", "SENTRY_PROJECT", "SENTRY_AUTH_TOKEN", "GH_TOKEN", "GH_REPOSITORY")
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise SystemExit(f"Missing configuration: {', '.join(missing)}")
    sync(*(os.environ[key] for key in required))
