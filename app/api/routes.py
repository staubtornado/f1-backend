"""HTTP endpoints delegating Formula 1 queries to the application service."""

from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.schemas.race_position import RacePosition
from app.services.f1 import F1Service


def get_f1_service(request: Request) -> F1Service:
    """
    Retrieve the service created during application startup.

    :param request: Request whose application state holds the shared service.
    :return: The application's F1 service.
    :raises AttributeError: If application startup has not initialized the service.
    """
    return request.app.state.f1


router = APIRouter()


@router.get("/seasons/")
async def get_sessions(client: F1Service = Depends(get_f1_service)):
    """
    Return available seasons in ascending order.

    :param client: F1 service supplied by FastAPI dependency injection.
    :return: List of season years.
    """
    return await client.get_seasons()


@router.get("/seasons/{season}/weekends/")
async def get_season_weekend(season: int, client: F1Service = Depends(get_f1_service)):
    """
    Return the meetings for a season with country flags.

    :param client: F1 service supplied by FastAPI dependency injection.
    :param season: The season year.
    :return: Weekend models, or an empty list.
    """
    return await client.get_season_weekends(season)


@router.get("/weekend/{weekend_id}/sessions/")
async def get_weekend_sessions(weekend_id: int, client: F1Service = Depends(get_f1_service)):
    """
    Return the sessions belonging to a meeting.

    :param client: F1 service supplied by FastAPI dependency injection.
    :param weekend_id: The OpenF1 meeting key.
    :return: Session models, including testing sessions when present.
    """
    return await client.get_weekend_sessions(weekend_id)


@router.get("/session/{session_id}/result/")
async def get_session_results(session_id: int, client: F1Service = Depends(get_f1_service)):
    """
    Return classifications for a session.

    :param client: F1 service supplied by FastAPI dependency injection.
    :param session_id: The OpenF1 session key.
    :return: Result model whose classifications may be empty.
    """
    return await client.get_session_results(session_id)


@router.get("/seasons/{season}/drivers/{driver_id}/")
async def get_season_drivers(season: int, driver_id: int, client: F1Service = Depends(get_f1_service)):
    """
    Return a driver's profile for a season.

    :param client: F1 service supplied by FastAPI dependency injection.
    :param season: The season year.
    :param driver_id: The driver's racing number.
    :return: Driver profile with an encoded portrait when available.
    :raises fastapi.HTTPException: HTTP 404 if no meeting or matching driver exists.
    """
    return await client.get_season_drivers(season, driver_id)


@router.get("/standings/{season}/driver_standings/")
async def get_driver_standings(season: int, client: F1Service = Depends(get_f1_service)):
    """
    Return driver championship standings for a season.

    :param client: F1 service supplied by FastAPI dependency injection.
    :param season: The season year.
    :return: Standings from the latest started eligible Race or Sprint session,
        or empty standings if none exists.
    """
    return await client.get_driver_standings(season)


@router.get("/standings/{season}/team_standings/")
async def get_season_team_standings(season: int, client: F1Service = Depends(get_f1_service)):
    """
    Return team championship standings for a season.

    :param client: F1 service supplied by FastAPI dependency injection.
    :param season: The season year.
    :return: Standings from a started Grand Prix in the latest eligible weekend,
        or empty standings if none exists.
    """
    return await client.get_season_team_standings(season)


@router.get("/weekend/{weekend_id}/starting_grid/")
async def get_session_starting_grid(weekend_id: int, client: F1Service = Depends(get_f1_service)):
    """
    Return starting grids associated with qualifying sessions.

    :param client: F1 service supplied by FastAPI dependency injection.
    :param weekend_id: The OpenF1 meeting key.
    :return: Grids for qualifying and sprint qualifying, with sorted positions.
    """
    return await client.get_session_starting_grid(weekend_id)


@router.get("/grand-prix/{session_id}/positions/", response_model=list[RacePosition])
async def get_grand_prix_session_positions(session_id: int, client: F1Service = Depends(get_f1_service)):
    """
    Return chronological position changes with driver profiles.

    :param client: F1 service supplied by FastAPI dependency injection.
    :param session_id: The OpenF1 session key; the session type is not checked.
    :return: Position updates for all drivers, or an empty list.
    :raises fastapi.HTTPException: HTTP 502 if an update references a missing driver.
    """
    return await client.get_grand_prix_session_positions(session_id)
