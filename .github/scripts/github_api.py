"""Read-only GitHub REST client for the consistency check and the metrics report.

Reads GITHUB_TOKEN and GITHUB_REPOSITORY, which GitHub Actions sets for every job.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

API = "https://api.github.com"
TITLE_KEY = re.compile(r"\[(SW-\d+)\]\s*$")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class GitHub:
    def __init__(self, repository: str, token: str) -> None:
        self.repository = repository
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    @classmethod
    def from_env(cls) -> GitHub:
        return cls(os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"])

    def get(self, path: str) -> Any:
        """GET a repository path; None when it does not exist."""
        request = urllib.request.Request(
            f"{API}/repos/{self.repository}/{path}", headers=self.headers
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise

    def pages(self, path: str, key: str | None = None) -> list[Any]:
        """All items of a paged list (100 per page)."""
        items: list[Any] = []
        separator = "&" if "?" in path else "?"
        for page in range(1, 51):
            data: Any = self.get(f"{path}{separator}per_page=100&page={page}") or []
            batch: list[Any] = data.get(key, []) if key else data
            items.extend(batch)
            if len(batch) < 100:
                break
        return items

    def merged_pulls(self) -> dict[str, dict[str, Any]]:
        """The latest merged pull request per story key in its title."""
        found: dict[str, dict[str, Any]] = {}
        for pull in self.pages("pulls?state=closed&sort=updated&direction=desc"):
            match = TITLE_KEY.search(pull["title"])
            if match and pull.get("merged_at") and match.group(1) not in found:
                found[match.group(1)] = pull
        return found

    def last_release(self, environment: str = "prod-release") -> datetime | None:
        """When the newest successful deployment to the release environment happened."""
        for deployment in self.get(f"deployments?environment={environment}&per_page=30") or []:
            statuses = self.get(f"deployments/{deployment['id']}/statuses") or []
            if any(status["state"] == "success" for status in statuses):
                return parse_time(deployment["created_at"])
        return None

    def workflow_runs(self, workflow: str, since: str) -> list[Any] | None:
        """Runs of a workflow file created on or after a date; None if it does not exist."""
        if self.get(f"actions/workflows/{workflow}") is None:
            return None
        return self.pages(f"actions/workflows/{workflow}/runs?created=>={since}", "workflow_runs")

    def changes_requested(self, number: int) -> int:
        reviews = self.pages(f"pulls/{number}/reviews")
        return sum(1 for review in reviews if review["state"] == "CHANGES_REQUESTED")
