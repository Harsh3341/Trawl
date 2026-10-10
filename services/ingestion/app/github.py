from __future__ import annotations
import os
from dataclasses import dataclass
import httpx


@dataclass(frozen=True)
class Release:
    url: str
    title: str
    version: str
    body: str


class GitHubReleaseClient:
    def __init__(self, token: str | None = None, base_url: str = "https://api.github.com") -> None:
        self._token = token or os.getenv("GITHUB_TOKEN") or ""
        self._base_url = base_url

    def fetch_releases(self, repo: str) -> list[Release]:
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        resp = httpx.get(f"{self._base_url}/repos/{repo}/releases", headers=headers, timeout=30)
        resp.raise_for_status()
        out: list[Release] = []
        for r in resp.json():
            title = r.get("name") or r.get("tag_name") or "untitled"
            out.append(Release(
                url=r["html_url"],
                title=title,
                version=r.get("tag_name") or "",
                body=r.get("body") or "",
            ))
        return out
