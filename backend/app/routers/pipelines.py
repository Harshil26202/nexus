import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import redis_pool
from app.models.pipeline import Pipeline, PipelineRun, PipelineStatus, RiskLevel

router = APIRouter()


class PipelineOut(BaseModel):
    id: uuid.UUID
    repo_full_name: str
    branch: str
    commit_sha: str
    commit_message: str | None
    author: str | None
    pr_number: int | None
    status: PipelineStatus
    risk_level: RiskLevel | None
    risk_score: float | None
    semantic_summary: str | None
    ai_recommendation: str | None
    gate_results: dict | None
    duration_seconds: int | None

    model_config = {"from_attributes": True}


class TriggerPipelineRequest(BaseModel):
    repo: str
    commit_sha: str
    commit_message: str = ""
    branch: str = "main"
    diff: str = ""
    changed_files: list[str] = []
    pr_number: int | None = None
    pr_description: str = ""


@router.get("/", response_model=list[PipelineOut])
async def list_pipelines(
    db: AsyncSession = Depends(get_db),
    repo: str | None = Query(None),
    status_filter: PipelineStatus | None = Query(None, alias="status"),
    limit: int = Query(20, le=100),
    offset: int = 0,
) -> list[Pipeline]:
    cache_key = f"pipelines:list:{repo}:{status_filter}:{limit}:{offset}"
    cached = await redis_pool.get(cache_key)
    if cached:
        return cached  # type: ignore[return-value]

    stmt = select(Pipeline).order_by(desc(Pipeline.created_at)).limit(limit).offset(offset)
    if repo:
        stmt = stmt.where(Pipeline.repo_full_name == repo)
    if status_filter:
        stmt = stmt.where(Pipeline.status == status_filter)

    result = await db.execute(stmt)
    pipelines = result.scalars().all()
    return list(pipelines)


@router.get("/{pipeline_id}", response_model=PipelineOut)
async def get_pipeline(pipeline_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Pipeline:
    cache_key = f"pipelines:{pipeline_id}"
    cached = await redis_pool.get(cache_key)
    if cached:
        return cached  # type: ignore[return-value]

    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline not found")

    await redis_pool.set(cache_key, PipelineOut.model_validate(pipeline).model_dump(), ttl=30)
    return pipeline


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_pipeline(
    body: TriggerPipelineRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    import asyncio

    from app.agents.orchestrator import orchestrator

    pipeline = Pipeline(
        repo_full_name=body.repo,
        branch=body.branch,
        commit_sha=body.commit_sha,
        commit_message=body.commit_message,
        pr_number=body.pr_number,
        status=PipelineStatus.RUNNING,
    )
    db.add(pipeline)
    await db.flush()
    pipeline_id = str(pipeline.id)

    asyncio.create_task(orchestrator.run_pipeline({
        "pipeline_id": pipeline_id,
        "repo": body.repo,
        "commit_sha": body.commit_sha,
        "commit_message": body.commit_message,
        "branch": body.branch,
        "diff": body.diff,
        "changed_files": body.changed_files,
        "pr_description": body.pr_description,
    }))

    return {"pipeline_id": pipeline_id, "status": "running"}


@router.get("/{pipeline_id}/runs", response_model=list[dict])
async def get_pipeline_runs(pipeline_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list:
    stmt = select(PipelineRun).where(PipelineRun.pipeline_id == pipeline_id)
    result = await db.execute(stmt)
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "step_name": r.step_name,
            "status": r.status,
            "duration_seconds": r.duration_seconds,
            "agent_name": r.agent_name,
        }
        for r in runs
    ]


@router.get("/{pipeline_id}/analysis")
async def get_pipeline_analysis(
    pipeline_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return {
        "semantic_summary": pipeline.semantic_summary,
        "blast_radius": pipeline.blast_radius,
        "selected_tests": pipeline.selected_tests,
        "skipped_tests": pipeline.skipped_tests,
        "gate_results": pipeline.gate_results,
        "ai_recommendation": pipeline.ai_recommendation,
        "risk_score": pipeline.risk_score,
        "risk_level": pipeline.risk_level,
    }
