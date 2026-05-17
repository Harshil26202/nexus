import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.quality_gate import GateType, QualityGate

router = APIRouter()


class QualityGateCreate(BaseModel):
    name: str
    repo_pattern: str = "*"
    gate_type: GateType
    threshold_value: float | None = None
    threshold_operator: str = "gte"
    adaptive_enabled: bool = True
    adaptive_prompt: str | None = None
    context_factors: dict | None = None
    description: str | None = None


class QualityGateOut(BaseModel):
    id: uuid.UUID
    name: str
    repo_pattern: str
    gate_type: GateType
    enabled: bool
    threshold_value: float | None
    threshold_operator: str
    adaptive_enabled: bool
    description: str | None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[QualityGateOut])
async def list_gates(db: AsyncSession = Depends(get_db)) -> list[QualityGate]:
    result = await db.execute(select(QualityGate))
    return list(result.scalars().all())


@router.post("/", response_model=QualityGateOut, status_code=201)
async def create_gate(body: QualityGateCreate, db: AsyncSession = Depends(get_db)) -> QualityGate:
    gate = QualityGate(**body.model_dump())
    db.add(gate)
    await db.flush()
    return gate


@router.patch("/{gate_id}/toggle", response_model=QualityGateOut)
async def toggle_gate(gate_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> QualityGate:
    result = await db.execute(select(QualityGate).where(QualityGate.id == gate_id))
    gate = result.scalar_one_or_none()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    gate.enabled = not gate.enabled
    return gate


@router.delete("/{gate_id}", status_code=204)
async def delete_gate(gate_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    result = await db.execute(select(QualityGate).where(QualityGate.id == gate_id))
    gate = result.scalar_one_or_none()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    await db.delete(gate)


@router.post("/evaluate")
async def evaluate_gates(payload: dict) -> dict:
    """Ad-hoc gate evaluation against supplied metrics."""
    from app.agents.quality_gate_agent import QualityGateAgent
    agent = QualityGateAgent()
    result = await agent.run(payload)
    return result.output
