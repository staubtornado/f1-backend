from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.services.f1 import F1Service


def get_f1_service(request: Request) -> F1Service:
    return request.app.state.f1


router = APIRouter()


@router.get("/seasons/")
async def get_sessions(client: F1Service = Depends(get_f1_service)):
    return await client.get_seasons()


@router.get("/seasons/{season}/weekends/")
async def get_season_weekend(season: int, client: F1Service = Depends(get_f1_service)):
    return await client.get_season_weekends(season)


@router.get("/weekend/{weekend_id}/sessions/")
async def get_weekend_sessions(weekend_id: int, client: F1Service = Depends(get_f1_service)):
    return await client.get_weekend_sessions(weekend_id)
