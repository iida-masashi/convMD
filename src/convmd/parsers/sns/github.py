"""GitHub repository / issue / discussion fetcher via the REST API."""

from __future__ import annotations

import base64
import logging
import os
import re
from pathlib import Path

from convmd.core.http import get_json
from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


def _auth_headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _api(endpoint: str):
    return get_json(f"https://api.github.com{endpoint}", headers=_auth_headers())


def _save_md(title: str, url: str, tags: list[str], body: str, output_dir: Path) -> Path:
    fm = generate_frontmatter(title, url, tags=tags)
    safe = sanitize_filename(title)
    path = output_dir / f"{safe}.md"
    path.write_text(fm + body, encoding="utf-8")
    logger.info(f"Saved GitHub content to {path}")
    return path


def convert_github_readme(owner: str, repo: str, output_dir: Path) -> Path | None:
    data = _api(f"/repos/{owner}/{repo}/readme")
    if not data:
        return None
    try:
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
    except Exception as e:
        logger.error(f"Failed to decode README for {owner}/{repo}: {e}")
        return None
    title = f"{owner}/{repo} README"
    url = f"https://github.com/{owner}/{repo}"
    return _save_md(title, url, ["github", "readme"], content, output_dir)


def convert_github_issue(owner: str, repo: str, num: str, output_dir: Path) -> Path | None:
    issue = _api(f"/repos/{owner}/{repo}/issues/{num}")
    if not issue:
        return None
    title = f"{owner}/{repo}#{num}: {issue.get('title', '')}"
    url = issue.get("html_url", f"https://github.com/{owner}/{repo}/issues/{num}")
    body_parts = [f"# {issue.get('title', '')}\n\n", issue.get("body", "") or "", "\n\n"]

    comments = _api(f"/repos/{owner}/{repo}/issues/{num}/comments") or []
    if comments:
        body_parts.append("## Comments\n\n")
        for c in comments:
            author = c.get("user", {}).get("login", "?")
            body_parts.append(f"**@{author}** ({c.get('created_at')}):\n\n{c.get('body', '')}\n\n---\n\n")

    return _save_md(title, url, ["github", "issue"], "".join(body_parts), output_dir)


def convert_github(url: str, output_dir: Path) -> Path | None:
    """Route github.com URLs to README / issue / discussion handlers."""
    issue_m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/issues/(\d+)", url)
    if issue_m:
        return convert_github_issue(issue_m.group(1), issue_m.group(2), issue_m.group(3), output_dir)

    pr_m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    if pr_m:
        # GitHub treats PRs as issues for the comments/body endpoint.
        return convert_github_issue(pr_m.group(1), pr_m.group(2), pr_m.group(3), output_dir)

    repo_m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/?$", url)
    if repo_m:
        return convert_github_readme(repo_m.group(1), repo_m.group(2), output_dir)

    logger.warning(f"Unrecognized GitHub URL shape: {url}")
    return None
