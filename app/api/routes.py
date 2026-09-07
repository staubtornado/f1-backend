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


@router.get("/session/{session_id}/result/")
async def get_session_results(session_id: int, client: F1Service = Depends(get_f1_service)):
    return await client.get_session_results(session_id)


@router.get("/seasons/{season}/drivers/{driver_id}")
async def get_season_drivers(season: int, driver_id: int, client: F1Service = Depends(get_f1_service)):
    return await client.get_season_drivers(season, driver_id)
