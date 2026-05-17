"""Natural Language DevOps chat endpoint — streaming + standard."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agents.orchestrator import orchestrator
from app.core.security import get_current_user

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    context: dict = {}  # e.g. current pipeline_id, repo


class ChatResponse(BaseModel):
    response: str
    intent: str | None = None
    tools_called: list[dict] = []
    follow_up_suggestions: list[str] = []
    requires_confirmation: bool = False


@router.post("/", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    _user: dict = Depends(get_current_user),
) -> ChatResponse:
    result = await orchestrator.run_chat({
        "message": body.message,
        "history": [m.model_dump() for m in body.history],
        "context": body.context,
    })
    return ChatResponse(
        response=result.get("response", ""),
        intent=result.get("intent"),
        tools_called=result.get("tools_to_call", []),
        follow_up_suggestions=result.get("follow_up_suggestions", []),
        requires_confirmation=result.get("requires_confirmation", False),
    )


@router.post("/public", response_model=ChatResponse)
async def chat_public(body: ChatRequest) -> ChatResponse:
    """Demo endpoint without auth — remove before prod."""
    result = await orchestrator.run_chat({
        "message": body.message,
        "history": [m.model_dump() for m in body.history],
        "context": body.context,
    })
    return ChatResponse(
        response=result.get("response", ""),
        intent=result.get("intent"),
        tools_called=result.get("tools_to_call", []),
        follow_up_suggestions=result.get("follow_up_suggestions", []),
        requires_confirmation=result.get("requires_confirmation", False),
    )
