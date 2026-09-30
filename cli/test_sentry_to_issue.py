"""Tests for the Sentry-to-GitHub issue bridge (no live API calls)."""

import io
from datetime import datetime, timezone
from urllib.error import HTTPError

import pytest

from scripts import sentry_to_issue as bridge

NOW = datetime(2026, 9, 30, tzinfo=timezone.utc)


def sentry_issue(issue_id, **overrides):
    issue = {
        "id": str(issue_id),
        "status": "unresolved",
        "level": "error",
        "lastSeen": "2026-09-30T00:00:00Z",
        "title": "private user text",
        "metadata": {"value": "private event data"},
    }
    issue.update(overrides)
    return issue


def test_sync_deduplicates_closed_and_open_issues_and_excludes_private_data(monkeypatch):
    posts = []

    def fake_pages(url, token):
        if url.startswith(bridge.GITHUB_API):
            return iter(
                [
                    {"body": bridge.new_issue("org", "web", "1")["body"], "state": "closed"},
                    {"body": bridge.new_issue("org", "web", "2")["body"], "state": "open"},
                ]
            )
        return iter([sentry_issue(1), sentry_issue(2), sentry_issue(3)])

    def fake_request(url, token, *, method="GET", data=None):
        posts.append((url, method, data))
        return {}, ""

    monkeypatch.setattr(bridge, "pages", fake_pages)
    monkeypatch.setattr(bridge, "request_json", fake_request)
    assert bridge.sync("org", "web", "sentry-token", "github-token", "owner/repo", NOW) == 1
    assert len(posts) == 1
    url, method, data = posts[0]
    assert (url, method) == ("https://api.github.com/repos/owner/repo/issues", "POST")
    assert "<!-- sentry-issue:org/web/3 -->" in data["body"]
    assert "https://org.sentry.io/issues/3/" in data["body"]
    assert "private" not in str(data)


def test_only_recent_unresolved_errors_are_created(monkeypatch):
    posts = []
    monkeypatch.setattr(
        bridge,
        "pages",
        lambda url, token: (
            iter([])
            if url.startswith(bridge.GITHUB_API)
            else iter(
                [
                    sentry_issue(1, lastSeen="2026-09-01T00:00:00Z"),
                    sentry_issue(2, status="resolved"),
                    sentry_issue(3, level="warning"),
                    sentry_issue(4, level="fatal"),
                ]
            )
        ),
    )
    monkeypatch.setattr(
        bridge,
        "request_json",
        lambda url, token, *, method="GET", data=None: (posts.append(data), ""),
    )
    assert bridge.sync("org", "web", "s", "g", "owner/repo", NOW) == 1
    assert posts[0]["title"] == "Investigate Sentry error web #4"


def test_creation_is_bounded_per_run(monkeypatch):
    posts = []
    monkeypatch.setattr(
        bridge,
        "pages",
        lambda url, token: (
            iter([])
            if url.startswith(bridge.GITHUB_API)
            else iter(sentry_issue(i) for i in range(20))
        ),
    )
    monkeypatch.setattr(
        bridge,
        "request_json",
        lambda url, token, *, method="GET", data=None: (posts.append(data), ""),
    )
    assert bridge.sync("org", "web", "s", "g", "owner/repo", NOW) == bridge.MAX_NEW_ISSUES
    assert len(posts) == bridge.MAX_NEW_ISSUES


def test_pagination_rejects_other_hosts_and_loops(monkeypatch):
    url = "https://sentry.io/api/0/projects/org/web/issues/?per_page=100"
    assert bridge.next_page(f'<{url}&cursor=abc>; rel="next"; results="true"', url) == (
        f"{url}&cursor=abc"
    )
    assert bridge.next_page(f'<{url}&cursor=abc>; rel="next"; results="false"', url) is None
    with pytest.raises(ValueError, match="Unexpected pagination URL"):
        bridge.next_page('<https://attacker.example/path>; rel="next"', url)
    monkeypatch.setattr(bridge, "request_json", lambda u, t: ([], f'<{u}>; rel="next"'))
    with pytest.raises(ValueError, match="Pagination loop"):
        list(bridge.pages(url, "token"))


def test_pages_follow_pagination_and_fail_on_malformed_response(monkeypatch):
    url = "https://api.github.com/repos/owner/repo/issues?state=all"
    next_url = f"{url}&page=2"
    responses = iter(
        [
            ([{"id": 1}], f'<{next_url}>; rel="next"'),
            ([{"id": 2}], ""),
        ]
    )
    monkeypatch.setattr(bridge, "request_json", lambda u, t: next(responses))
    assert list(bridge.pages(url, "token")) == [{"id": 1}, {"id": 2}]
    monkeypatch.setattr(bridge, "request_json", lambda u, t: ({"error": "bad response"}, ""))
    with pytest.raises(ValueError, match="Expected an API list"):
        list(bridge.pages(url, "token"))


def test_api_error_does_not_include_private_response(monkeypatch):
    def fail(request, timeout):
        raise HTTPError(
            request.full_url, 403, "Forbidden", {}, io.BytesIO(b"private event details")
        )

    monkeypatch.setattr(bridge, "urlopen", fail)
    with pytest.raises(RuntimeError, match="GET /api/0/issues/ failed") as exc:
        bridge.request_json("https://sentry.io/api/0/issues/", "private-token")
    assert "private event details" not in str(exc.value)
    assert "private-token" not in str(exc.value)


def test_rejects_invalid_project_and_issue_ids():
    with pytest.raises(ValueError, match="slugs"):
        bridge.sync("org.example", "web", "s", "g", "owner/repo", NOW)
    with pytest.raises(ValueError, match="issue ID"):
        bridge.new_issue("org", "web", "1/../../private")
