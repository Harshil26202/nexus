"""GitHub & Azure DevOps webhook receivers.

Full flow for GitHub:
  1. Receive webhook (push / pull_request)
  2. Verify HMAC-SHA256 signature
  3. Create Pipeline DB record
  4. Fetch actual diff from GitHub API
  5. Enqueue to Service Bus OR run directly
  6. Post "pending" commit status to GitHub
  7. Worker picks up task → runs agents → updates DB → posts final status
"""
import hashlib
import hmac
import json
import uuid

import structlog
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from app.agents.orchestrator import orchestrator
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.pipeline import Pipeline, PipelineStatus
from app.services.pipeline_service import pipeline_service

log = structlog.get_logger()
router = APIRouter()


def _verify_github_sig(body: bytes, sig: str) -> bool:
    if not settings.GITHUB_WEBHOOK_SECRET:
        return True
    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, sig)


async def _create_pipeline_record(
    repo: str,
    commit_sha: str,
    commit_message: str,
    branch: str,
    author: str = "",
    pr_number: int | None = None,
) -> str:
    async with AsyncSessionLocal() as session:
        p = Pipeline(
            repo_full_name=repo,
            branch=branch,
            commit_sha=commit_sha,
            commit_message=commit_message,
            author=author,
            pr_number=pr_number,
            status=PipelineStatus.RUNNING,
        )
        session.add(p)
        await session.commit()
        return str(p.id)


async def _run_pipeline_full(
    repo: str,
    commit_sha: str,
    commit_message: str,
    branch: str,
    author: str,
    pr_number: int | None,
    pr_description: str,
    pipeline_id: str,
    github_token: str = "",
) -> None:
    log.info("webhook.pipeline_start", repo=repo, sha=commit_sha[:7], pipeline_id=pipeline_id[:8])

    # Post "pending" status to GitHub
    await pipeline_service.post_github_status(
        repo=repo, sha=commit_sha,
        state="pending",
        description="NEXUS analysis in progress...",
        github_token=github_token,
        pipeline_id=pipeline_id,
    )

    # Build full payload (fetches diff from GitHub)
    payload = await pipeline_service.build_payload(
        repo=repo,
        commit_sha=commit_sha,
        commit_message=commit_message,
        branch=branch,
        pr_number=pr_number,
        pr_description=pr_description,
        author=author,
        github_token=github_token,
        pipeline_id=pipeline_id,
    )

    # Run through agent orchestrator
    result = await orchestrator.run_pipeline(payload)

    # Update DB record
    can_deploy = result.get("can_deploy", False)
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        res = await session.execute(
            select(Pipeline).where(Pipeline.id == uuid.UUID(pipeline_id))
        )
        p = res.scalar_one_or_none()
        if p:
            stages = result.get("stages", {})
            semantic = stages.get("semantic_analysis", {}).get("output", {})
            test_intel = stages.get("test_intelligence", {}).get("output", {})
            gate = stages.get("quality_gate", {}).get("output", {})

            p.status = PipelineStatus.SUCCESS if can_deploy else PipelineStatus.FAILED
            p.risk_level = semantic.get("risk_level")
            p.risk_score = semantic.get("risk_score")
            p.semantic_summary = semantic.get("summary")
            p.blast_radius = semantic.get("blast_radius")
            p.selected_tests = test_intel.get("must_run", []) + test_intel.get("should_run", [])
            p.skipped_tests = test_intel.get("skip", [])
            p.gate_results = gate
            p.ai_recommendation = gate.get("risk_summary")
            p.duration_seconds = result.get("total_duration_ms", 0) // 1000
            await session.commit()

    # Post final status to GitHub
    if github_token:
        state = "success" if can_deploy else "failure"
        risk = result.get("risk_level", "unknown")
        rec = gate.get("deploy_recommendation", "unknown") if "gate" in dir() else "unknown"
        await pipeline_service.post_github_status(
            repo=repo, sha=commit_sha,
            state=state,
            description=f"NEXUS: {rec} | risk={risk} | {'' if can_deploy else 'BLOCKED'}",
            github_token=github_token,
            pipeline_id=pipeline_id,
        )

    # Post PR comment with AI analysis
    if pr_number and github_token and semantic:
        comment = _build_pr_comment(result, pipeline_id)
        await __import__("app.services.github_service", fromlist=["github_service"]).github_service.add_pr_comment(
            repo=repo, pr_number=pr_number, body=comment, token=github_token
        )

    log.info("webhook.pipeline_complete", pipeline_id=pipeline_id[:8], can_deploy=can_deploy)


def _build_pr_comment(result: dict, pipeline_id: str) -> str:
    stages = result.get("stages", {})
    semantic = stages.get("semantic_analysis", {}).get("output", {})
    gate = stages.get("quality_gate", {}).get("output", {})
    test_intel = stages.get("test_intelligence", {}).get("output", {})

    risk = semantic.get("risk_level", "unknown")
    score = semantic.get("risk_score", 0)
    can_deploy = result.get("can_deploy", False)
    status_emoji = "✅" if can_deploy else "🚫"

    lines = [
        f"## {status_emoji} NEXUS AI Analysis",
        "",
        f"**Risk Score:** {score:.0f}/100 &nbsp;·&nbsp; **Level:** `{risk}`",
        "",
        "### Summary",
        semantic.get("summary", "_Not available_"),
        "",
    ]

    blast = semantic.get("blast_radius", {})
    if any(blast.values()):
        lines += ["### Blast Radius", ""]
        for key, vals in blast.items():
            if vals:
                lines.append(f"- **{key.replace('_', ' ').title()}:** {', '.join(vals)}")
        lines.append("")

    gate_overall = gate.get("overall", "unknown")
    lines += [
        f"### Quality Gates: `{gate_overall.upper()}`",
        "",
    ]
    for g in gate.get("gates", []):
        icon = "✅" if g.get("result") == "pass" else "⚠️" if g.get("result") == "warn" else "❌"
        lines.append(f"- {icon} **{g['name']}** — {g.get('reasoning', '')[:100]}")

    saved = test_intel.get("time_saved_percent", 0)
    must_run = len(test_intel.get("must_run", []))
    skipped = len(test_intel.get("skip", []))
    lines += [
        "",
        "### Test Intelligence",
        f"Running **{must_run}** tests, skipping **{skipped}** · **{saved}% CI time saved**",
        "",
        "---",
        f"_[View full analysis](https://nexus.yourdomain.com/pipelines/{pipeline_id}) · Powered by NEXUS AI_",
    ]
    return "\n".join(lines)


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    background: BackgroundTasks,
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default=""),
) -> dict:
    body = await request.body()

    if not _verify_github_sig(body, x_hub_signature_256):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    log.info("webhook.github_received", event=x_github_event)

    if x_github_event == "ping":
        return {"message": "pong", "zen": payload.get("zen")}

    # Extract GitHub installation token if available (GitHub App flow)
    github_token = settings.GITHUB_APP_PRIVATE_KEY  # simplified for demo

    if x_github_event == "push":
        commits = payload.get("commits", [])
        if not commits:
            return {"accepted": False, "reason": "no_commits"}
        head = commits[-1]
        repo = payload.get("repository", {}).get("full_name", "")
        pipeline_id = await _create_pipeline_record(
            repo=repo,
            commit_sha=head.get("id", ""),
            commit_message=head.get("message", ""),
            branch=payload.get("ref", "").replace("refs/heads/", ""),
            author=head.get("author", {}).get("name", ""),
        )
        background.add_task(
            _run_pipeline_full,
            repo=repo,
            commit_sha=head.get("id", ""),
            commit_message=head.get("message", ""),
            branch=payload.get("ref", "").replace("refs/heads/", ""),
            author=head.get("author", {}).get("name", ""),
            pr_number=None,
            pr_description="",
            pipeline_id=pipeline_id,
            github_token=github_token,
        )

    elif x_github_event == "pull_request":
        action = payload.get("action")
        if action not in ("opened", "synchronize", "reopened"):
            return {"accepted": False, "reason": f"action_{action}_ignored"}
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {}).get("full_name", "")
        pipeline_id = await _create_pipeline_record(
            repo=repo,
            commit_sha=pr.get("head", {}).get("sha", ""),
            commit_message=pr.get("title", ""),
            branch=pr.get("head", {}).get("ref", ""),
            author=pr.get("user", {}).get("login", ""),
            pr_number=pr.get("number"),
        )
        background.add_task(
            _run_pipeline_full,
            repo=repo,
            commit_sha=pr.get("head", {}).get("sha", ""),
            commit_message=pr.get("title", ""),
            branch=pr.get("head", {}).get("ref", ""),
            author=pr.get("user", {}).get("login", ""),
            pr_number=pr.get("number"),
            pr_description=pr.get("body", ""),
            pipeline_id=pipeline_id,
            github_token=github_token,
        )

    return {"accepted": True, "event": x_github_event, "pipeline_id": pipeline_id}


@router.post("/azure-devops", status_code=status.HTTP_202_ACCEPTED)
async def azure_devops_webhook(request: Request, background: BackgroundTasks) -> dict:
    payload = await request.json()
    event_type = payload.get("eventType", "")
    log.info("webhook.azuredevops_received", event=event_type)

    if event_type in ("git.push", "git.pullrequest.created", "git.pullrequest.updated"):
        resource = payload.get("resource", {})
        repo = resource.get("repository", {}).get("name", "")
        commit_sha = resource.get("commits", [{}])[-1].get("commitId", "")
        pipeline_id = await _create_pipeline_record(
            repo=repo, commit_sha=commit_sha,
            commit_message=resource.get("commits", [{}])[-1].get("comment", ""),
            branch=resource.get("refUpdates", [{}])[0].get("name", "").replace("refs/heads/", ""),
        )
        background.add_task(
            _run_pipeline_full,
            repo=repo, commit_sha=commit_sha,
            commit_message=resource.get("commits", [{}])[-1].get("comment", ""),
            branch=resource.get("refUpdates", [{}])[0].get("name", "").replace("refs/heads/", ""),
            author="", pr_number=None, pr_description="",
            pipeline_id=pipeline_id,
        )

    return {"accepted": True, "event": event_type}


@router.post("/pagerduty", status_code=status.HTTP_202_ACCEPTED)
async def pagerduty_webhook(request: Request, background: BackgroundTasks) -> dict:
    payload = await request.json()
    for msg in payload.get("messages", []):
        if msg.get("event") == "incident.trigger":
            incident = msg.get("incident", {})
            background.add_task(orchestrator.run_incident, {
                "alert": {"name": incident.get("title", ""), "id": incident.get("id")},
                "service": incident.get("service", {}).get("name", ""),
                "recent_deploys": [],
                "error_logs": "",
                "metrics_anomalies": {},
            })
    return {"accepted": True}
