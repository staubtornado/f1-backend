from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.services.openf1 import OpenF1


def get_openf1_client(request: Request) -> OpenF1:
    return request.app.state.openf1


router = APIRouter()


@router.get("/sessions")
async def get_sessions(client: OpenF1 = Depends(get_openf1_client), year: int = 2026):
    return await client.get_sessions(year)
