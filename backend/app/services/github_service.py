"""GitHub API service — fetches diffs, posts statuses, creates issues."""

import httpx
import structlog

log = structlog.get_logger()


class GitHubService:
    BASE = "https://api.github.com"

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=self.BASE,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15.0,
        )

    def _auth_header(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    async def get_pr_diff(self, repo: str, pr_number: int, token: str) -> str:
        resp = await self._http.get(
            f"/repos/{repo}/pulls/{pr_number}",
            headers={**self._auth_header(token), "Accept": "application/vnd.github.v3.diff"},
        )
        resp.raise_for_status()
        return resp.text

    async def get_commit_diff(self, repo: str, sha: str, token: str) -> str:
        resp = await self._http.get(
            f"/repos/{repo}/commits/{sha}",
            headers={**self._auth_header(token), "Accept": "application/vnd.github.v3.diff"},
        )
        resp.raise_for_status()
        return resp.text

    async def get_changed_files(self, repo: str, sha: str, token: str) -> list[str]:
        resp = await self._http.get(
            f"/repos/{repo}/commits/{sha}",
            headers=self._auth_header(token),
        )
        resp.raise_for_status()
        return [f["filename"] for f in resp.json().get("files", [])]

    async def set_commit_status(
        self,
        repo: str,
        sha: str,
        state: str,  # "pending" | "success" | "failure" | "error"
        description: str,
        context: str,
        token: str,
        target_url: str = "",
    ) -> bool:
        payload = {
            "state": state,
            "description": description[:140],
            "context": context,
        }
        if target_url:
            payload["target_url"] = target_url
        try:
            resp = await self._http.post(
                f"/repos/{repo}/statuses/{sha}",
                json=payload,
                headers=self._auth_header(token),
            )
            return resp.status_code == 201
        except Exception as exc:
            log.warning("github.status_failed", error=str(exc))
            return False

    async def create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        labels: list[str],
        token: str,
    ) -> str | None:
        try:
            resp = await self._http.post(
                f"/repos/{repo}/issues",
                json={"title": title, "body": body, "labels": labels},
                headers=self._auth_header(token),
            )
            if resp.status_code == 201:
                return resp.json().get("html_url")
        except Exception as exc:
            log.warning("github.create_issue_failed", error=str(exc))
        return None

    async def add_pr_comment(self, repo: str, pr_number: int, body: str, token: str) -> bool:
        try:
            resp = await self._http.post(
                f"/repos/{repo}/issues/{pr_number}/comments",
                json={"body": body},
                headers=self._auth_header(token),
            )
            return resp.status_code == 201
        except Exception as exc:
            log.warning("github.pr_comment_failed", error=str(exc))
            return False

    async def close(self) -> None:
        await self._http.aclose()


github_service = GitHubService()
