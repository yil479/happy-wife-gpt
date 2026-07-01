import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from backend.auth import require_api_key
from backend.models.schemas import ChatRequest, ChatResponse, SourceChunk
from backend.rate_limit import limiter

router = APIRouter(tags=["chat"], dependencies=[Depends(require_api_key)])


async def _sse_generator(session_id: str, message: str, collection: str, engine):
    async for token in engine.chat_stream(session_id, message, collection):
        yield f"data: {json.dumps({'token': token})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/chat")
@limiter.limit("20/minute")
async def chat(req: ChatRequest, request: Request):
    engine = request.app.state.engine

    if req.stream:
        return StreamingResponse(
            _sse_generator(req.session_id, req.message, req.collection, engine),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    result = await engine.chat(req.session_id, req.message, req.collection)
    return ChatResponse(
        session_id=req.session_id,
        answer=result["answer"],
        sources=[SourceChunk(**s) for s in result["sources"]],
    )
