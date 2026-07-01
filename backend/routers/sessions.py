import uuid

from fastapi import APIRouter, Depends, Request

from backend.auth import require_api_key
from backend.models.schemas import ChatHistoryMessage, SessionHistoryResponse, SessionResponse

router = APIRouter(tags=["sessions"])


@router.post("/sessions", response_model=SessionResponse, dependencies=[Depends(require_api_key)])
async def create_session(request: Request) -> SessionResponse:
    session_id = str(uuid.uuid4())
    request.app.state.history.create_session(session_id)
    return SessionResponse(session_id=session_id)


@router.get(
    "/sessions/{session_id}/history",
    response_model=SessionHistoryResponse,
    dependencies=[Depends(require_api_key)],
)
async def get_session_history(session_id: str, request: Request) -> SessionHistoryResponse:
    rows = request.app.state.history.load_history(session_id)
    return SessionHistoryResponse(messages=[ChatHistoryMessage(**r) for r in rows])
