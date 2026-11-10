"""Jira script: the only way agents and CI touch Jira (ADR-010, ADR-011).

Offers what the roles need and nothing more: read a story, comment tagged with
the role, set the refinement verdict, move a story to a state the role may move
it to, and push a batch of stories to Backlog. Reads JIRA_BASE_URL,
JIRA_USER_EMAIL and JIRA_API_TOKEN from the environment (the agent account).

    python3 .github/scripts/jira.py get SW-12
    python3 .github/scripts/jira.py comment SW-12 --role refine --body "..."
    python3 .github/scripts/jira.py verdict SW-12 --verdict ready --reason "..."
    python3 .github/scripts/jira.py move SW-12 "Ready" --role refine
    python3 .github/scripts/jira.py push stories.json --role plan
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

PROJECT = "SW"
KEY = re.compile(rf"^{PROJECT}-\d+$")
# Who moves a story into which state: the table in ADR-010.
MOVES: dict[str, set[str]] = {
    "plan": set(),
    "refine": {"Ready", "Needs input"},
    "spec": {"Spec review"},
    "implement": {"In review"},
    "review": set(),
    "ci": {"In progress", "In review", "Awaiting release", "Done"},
}
# Comment tag per role, so one agent account still shows who spoke.
TAGS = {
    "plan": "planning",
    "refine": "refinement",
    "spec": "spec",
    "implement": "implementation",
    "review": "review",
    "ci": "ci",
}
VERDICTS = ("ready", "questions", "split")
VERDICT_FIELD = "Refinement verdict"


class JiraError(Exception):
    """A refused or failed Jira call, with a message fit for the run log."""


def allowed(role: str, status: str) -> bool:
    return status.casefold() in {s.casefold() for s in MOVES.get(role, set())}


def tagged(role: str, body: str) -> str:
    return f"[{TAGS[role]}] {body.strip()}"


def check_key(key: str) -> str:
    if not KEY.match(key):
        raise JiraError(f"{key!r} is not a {PROJECT} story key")
    return key


class Jira:
    """A thin REST client for the agent account."""

    def __init__(self, base_url: str, email: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        auth = base64.b64encode(f"{email}:{token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @classmethod
    def from_env(cls) -> Jira:
        names = ("JIRA_BASE_URL", "JIRA_USER_EMAIL", "JIRA_API_TOKEN")
        missing = [name for name in names if not os.environ.get(name)]
        if missing:
            raise JiraError(f"missing environment variables: {', '.join(missing)}")
        return cls(*(os.environ[name] for name in names))

    def call(self, method: str, path: str, body: Any = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self.base_url + path, data=data, headers=self.headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:500]
            raise JiraError(f"{method} {path}: HTTP {error.code} {detail}") from error
        return json.loads(raw) if raw else None

    # Reading

    def issue(self, key: str, fields: str = "summary,status,labels,description") -> Any:
        query = urllib.parse.urlencode({"fields": fields})
        return self.call("GET", f"/rest/api/2/issue/{check_key(key)}?{query}")

    def search(self, jql: str, fields: str = "summary,status,labels") -> list[Any]:
        """All issues matching the JQL, following the page token."""
        issues: list[Any] = []
        token: str | None = None
        while True:
            params = {"jql": jql, "fields": fields, "maxResults": "100"}
            if token:
                params["nextPageToken"] = token
            page = self.call("GET", "/rest/api/3/search/jql?" + urllib.parse.urlencode(params))
            issues.extend(page.get("issues", []))
            token = page.get("nextPageToken")
            if not token or page.get("isLast", True):
                return issues

    def changelog(self, key: str) -> list[Any]:
        """Every history entry of a story, oldest first."""
        entries: list[Any] = []
        start = 0
        while True:
            path = f"/rest/api/2/issue/{check_key(key)}/changelog?startAt={start}&maxResults=100"
            page = self.call("GET", path)
            entries.extend(page.get("values", []))
            start += len(page.get("values", []))
            if page.get("isLast", True) or not page.get("values"):
                return entries

    # Writing, each limited to what a role may do

    def comment(self, key: str, role: str, body: str) -> None:
        self.call(
            "POST", f"/rest/api/2/issue/{check_key(key)}/comment", {"body": tagged(role, body)}
        )

    def verdict(self, key: str, verdict: str, reason: str) -> None:
        if verdict not in VERDICTS:
            raise JiraError(f"verdict must be one of {', '.join(VERDICTS)}")
        fields = self.call("GET", "/rest/api/2/field")
        field = next((f["id"] for f in fields if f.get("name") == VERDICT_FIELD), None)
        if field is None:
            raise JiraError(f"Jira has no field {VERDICT_FIELD!r}; Rafal creates it once")
        text = f"{verdict}: {reason.strip()}"
        self.call("PUT", f"/rest/api/2/issue/{check_key(key)}", {"fields": {field: text}})
        self.comment(key, "refine", f"Verdict: {text}")

    def move(self, key: str, status: str, role: str) -> None:
        if not allowed(role, status):
            raise JiraError(f"role {role!r} may not move a story to {status!r} (ADR-010)")
        path = f"/rest/api/2/issue/{check_key(key)}/transitions"
        transitions = self.call("GET", path)["transitions"]
        match = [t for t in transitions if t["to"]["name"].casefold() == status.casefold()]
        if not match:
            raise JiraError(f"{key} cannot move to {status!r} from its current state")
        self.call("POST", path, {"transition": {"id": match[0]["id"]}})

    def push(self, stories: list[dict[str, Any]]) -> list[str]:
        """Create stories in Backlog, or update ones still in Backlog."""
        keys: list[str] = []
        for story in stories:
            fields: dict[str, Any] = {
                "summary": story["summary"],
                "description": story.get("description", ""),
                "labels": story.get("labels", []),
            }
            if story.get("epic"):
                fields["parent"] = {"key": check_key(story["epic"])}
            key = story.get("key")
            if key:
                status = self.issue(key, "status")["fields"]["status"]["name"]
                if status != "Backlog":
                    raise JiraError(f"{key} is {status!r}; only Backlog stories can be pushed")
                self.call("PUT", f"/rest/api/2/issue/{key}", {"fields": fields})
            else:
                fields["project"] = {"key": PROJECT}
                fields["issuetype"] = {"name": story.get("type", "Story")}
                key = self.call("POST", "/rest/api/2/issue", {"fields": fields})["key"]
            keys.append(str(key))
        return keys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    get = commands.add_parser("get", help="print a story as JSON")
    get.add_argument("key")
    comment = commands.add_parser("comment", help="comment, tagged with the role")
    comment.add_argument("key")
    comment.add_argument("--role", choices=sorted(TAGS), required=True)
    comment.add_argument("--body", required=True)
    verdict = commands.add_parser("verdict", help="set the refinement verdict")
    verdict.add_argument("key")
    verdict.add_argument("--verdict", choices=VERDICTS, required=True)
    verdict.add_argument("--reason", required=True)
    move = commands.add_parser("move", help="move a story to a state the role may set")
    move.add_argument("key")
    move.add_argument("status")
    move.add_argument("--role", choices=sorted(MOVES), required=True)
    push = commands.add_parser("push", help="create or update a batch of Backlog stories")
    push.add_argument("file", help="JSON list of {key?, summary, description, labels, epic}")
    push.add_argument("--role", choices=["plan"], required=True)
    args = parser.parse_args(argv)

    try:
        jira = Jira.from_env()
        if args.command == "get":
            print(json.dumps(jira.issue(args.key), indent=2))
        elif args.command == "comment":
            jira.comment(args.key, args.role, args.body)
        elif args.command == "verdict":
            jira.verdict(args.key, args.verdict, args.reason)
        elif args.command == "move":
            jira.move(args.key, args.status, args.role)
        elif args.command == "push":
            with open(args.file, encoding="utf-8") as handle:
                print("\n".join(jira.push(json.load(handle))))
    except JiraError as error:
        print(f"jira: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
