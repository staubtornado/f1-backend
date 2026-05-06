from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.services.openf1 import OpenF1


def get_openf1_client(request: Request) -> OpenF1:
    return request.app.state.openf1


router = APIRouter()


@router.get("/seasons/")
async def get_sessions(client: OpenF1 = Depends(get_openf1_client)):
    return await client.get_seasons()


@router.get("/seasons/{season}/races/")
async def get_season_races(season: int, client: OpenF1 = Depends(get_openf1_client)):
    return await client.get_season_races(season)


@router.get("/races/{race_id}/sessions/")
async def get_race_sessions(races_id: int, client: OpenF1 = Depends(get_openf1_client)):
    pass
