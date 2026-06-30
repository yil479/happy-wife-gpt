from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(request: Request, key: str | None = Security(_header)) -> None:
    settings = request.app.state.settings
    if not settings.api_key:
        return  # auth disabled when API_KEY is not configured
    if key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
