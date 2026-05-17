import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.incident import Incident, IncidentSeverity, IncidentStatus

router = APIRouter()


class CreateIncidentRequest(BaseModel):
    title: str
    severity: IncidentSeverity
    service: str
    environment: str = "production"
    alert_payload: dict = {}
    recent_deploys: list[dict] = []
    error_logs: str = ""
    metrics_anomalies: dict = {}


class IncidentOut(BaseModel):
    id: uuid.UUID
    title: str
    severity: IncidentSeverity
    status: IncidentStatus
    service: str
    environment: str
    root_cause_commit: str | None
    root_cause_analysis: str | None
    rollback_safe: bool | None = None
    slack_summary: str | None = None
    pagerduty_id: str | None
    resolved_at: str | None
    mttr_seconds: int | None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[IncidentOut])
async def list_incidents(
    db: AsyncSession = Depends(get_db),
    status_filter: IncidentStatus | None = Query(None, alias="status"),
    severity: IncidentSeverity | None = None,
    service: str | None = None,
    limit: int = Query(20, le=100),
) -> list[Incident]:
    stmt = select(Incident).order_by(desc(Incident.created_at)).limit(limit)
    if status_filter:
        stmt = stmt.where(Incident.status == status_filter)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if service:
        stmt = stmt.where(Incident.service == service)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=dict, status_code=202)
async def create_incident(
    body: CreateIncidentRequest,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.agents.orchestrator import orchestrator

    incident = Incident(
        title=body.title,
        severity=body.severity,
        service=body.service,
        environment=body.environment,
        status=IncidentStatus.INVESTIGATING,
    )
    db.add(incident)
    await db.flush()
    incident_id = str(incident.id)

    async def run_and_update() -> None:
        result = await orchestrator.run_incident({
            "alert": {"name": body.title, **body.alert_payload},
            "service": body.service,
            "recent_deploys": body.recent_deploys,
            "error_logs": body.error_logs,
            "metrics_anomalies": body.metrics_anomalies,
        })
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Incident).where(Incident.id == incident.id))
            inc = res.scalar_one()
            inc.root_cause_commit = result.get("root_cause_commit")
            inc.root_cause_analysis = result.get("root_cause_summary")
            inc.postmortem_draft = str(result.get("postmortem_draft", {}))
            inc.suggested_fix = str(result.get("suggested_fix", {}))
            inc.affected_services = result.get("affected_services", [])
            inc.status = IncidentStatus.IDENTIFIED
            await session.commit()

    background.add_task(run_and_update)
    return {"incident_id": incident_id, "status": "investigating", "analysis": "in_progress"}


@router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Incident:
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.patch("/{incident_id}/resolve")
async def resolve_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from datetime import datetime, timezone
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    now = datetime.now(timezone.utc)
    incident.status = IncidentStatus.RESOLVED
    incident.resolved_at = now.isoformat()
    if incident.created_at:
        incident.mttr_seconds = int((now - incident.created_at).total_seconds())
    return {"resolved": True, "mttr_seconds": incident.mttr_seconds}
