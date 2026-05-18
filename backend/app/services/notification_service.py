"""Multi-channel notification service: Slack, Teams, PagerDuty."""

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger()


class NotificationService:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=10.0)

    async def send_slack(self, message: str, blocks: list | None = None) -> bool:
        if not settings.SLACK_WEBHOOK_URL:
            return False
        payload: dict = {"text": message}
        if blocks:
            payload["blocks"] = blocks
        try:
            resp = await self._http.post(settings.SLACK_WEBHOOK_URL, json=payload)
            return resp.status_code == 200
        except Exception as exc:
            log.warning("notification.slack_failed", error=str(exc))
            return False

    async def send_teams(self, title: str, message: str, color: str = "0076D7") -> bool:
        if not settings.MICROSOFT_TEAMS_WEBHOOK_URL:
            return False
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color,
            "summary": title,
            "sections": [{"activityTitle": title, "activityText": message}],
        }
        try:
            resp = await self._http.post(settings.MICROSOFT_TEAMS_WEBHOOK_URL, json=card)
            return resp.status_code == 200
        except Exception as exc:
            log.warning("notification.teams_failed", error=str(exc))
            return False

    async def create_pagerduty_incident(self, title: str, service_id: str, severity: str) -> str | None:
        if not settings.PAGERDUTY_API_KEY:
            return None
        payload = {
            "incident": {
                "type": "incident",
                "title": title,
                "service": {"id": service_id, "type": "service_reference"},
                "urgency": "high" if severity in ("sev1", "sev2") else "low",
            }
        }
        try:
            resp = await self._http.post(
                "https://api.pagerduty.com/incidents",
                json=payload,
                headers={
                    "Authorization": f"Token token={settings.PAGERDUTY_API_KEY}",
                    "From": "nexus@yourcompany.com",
                },
            )
            if resp.status_code == 201:
                return resp.json()["incident"]["id"]
        except Exception as exc:
            log.warning("notification.pagerduty_failed", error=str(exc))
        return None

    async def notify_pipeline_failure(self, pipeline: dict) -> None:
        repo = pipeline.get("repo_full_name", "unknown")
        sha = pipeline.get("commit_sha", "")[:7]
        risk = pipeline.get("risk_level", "unknown")
        message = f"Pipeline FAILED | {repo} | {sha} | Risk: {risk}"
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "Pipeline Failed"}},
            {"type": "section", "text": {"type": "mrkdwn",
                "text": f"*Repo:* {repo}\n*Commit:* `{sha}`\n*Risk:* {risk}"}},
        ]
        await self.send_slack(message, blocks)
        await self.send_teams("Pipeline Failed", message, "FF0000")

    async def notify_incident_created(self, incident: dict) -> None:
        severity = incident.get("severity", "")
        service = incident.get("service", "")
        title = incident.get("title", "")
        message = f"[{severity.upper()}] Production Incident | {service} | {title}"
        await self.send_slack(message)
        await self.send_teams(f"Incident: {title}", message, "FF0000")

    async def close(self) -> None:
        await self._http.aclose()


notification_service = NotificationService()
