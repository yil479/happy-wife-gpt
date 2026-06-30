import uuid

from fastapi import APIRouter, Depends

from backend.auth import require_api_key
from backend.models.schemas import SessionResponse

router = APIRouter(tags=["sessions"])


@router.post("/sessions", response_model=SessionResponse, dependencies=[Depends(require_api_key)])
async def create_session() -> SessionResponse:
    return SessionResponse(session_id=str(uuid.uuid4()))
