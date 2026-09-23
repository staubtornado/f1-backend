from asyncio import gather
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import TypeVar

from pydantic import TypeAdapter
from redis.asyncio import Redis

from app.schemas.starting_grid import StartingGrid
from app.schemas.starting_positon import StartingPosition
from app.schemas.team_standings import TeamStandings
from app.schemas.classification import Classification
from app.schemas.country import Country
from app.schemas.driver import Driver
from app.schemas.driver_standing import DriverStanding
from app.schemas.driver_standings import DriverStandings
from app.schemas.result import Result
from app.schemas.session import Session
from app.schemas.session_type import SessionType
from app.schemas.team_standing import TeamStanding
from app.schemas.weekend import Weekend
from app.services.openf1 import OpenF1, RedisCache


T = TypeVar("T")
SEASONS = TypeAdapter(list[int])
WEEKENDS = TypeAdapter(list[Weekend])
SESSIONS = TypeAdapter(list[Session])
RESULT = TypeAdapter(Result)
DRIVER = TypeAdapter(Driver)
DRIVER_STANDINGS = TypeAdapter(DriverStandings)
TEAM_STANDINGS = TypeAdapter(TeamStandings)
STARTING_GRIDS = TypeAdapter(list[StartingGrid])

DAY = 60 * 60 * 24
WEEK = DAY * 7
EMPTY_TTL = 30


class F1Service:
    def __init__(self, openf1: OpenF1, redis: Redis) -> None:
        self._openf1 = openf1
        self._cache = RedisCache(redis)
        self._openf1.set_cache(self._cache)

    async def _cached(
            self,
            key: str,
            adapter: TypeAdapter[T],
            fetch: Callable[[], Awaitable[T]],
            ttl: int | Callable[[T], int],
    ) -> T:
        async def load() -> tuple[bytes, int]:
            result = await fetch()
            return adapter.dump_json(result), ttl if isinstance(ttl, int) else ttl(result)

        # v2 uses one JSON document, including for lists of models. Old keys
        # contain JSON strings inside JSON arrays and expire independently.
        data = await self._cache.get_or_load(f"f1:v2:{key}", load)
        return adapter.validate_json(data)

    @staticmethod
    def _season_ttl(season: int) -> int:
        return WEEK if season < datetime.now(timezone.utc).year else 60 * 60

    async def get_seasons(self) -> list[int]:
        return await self._cached(
            "seasons", SEASONS, self._openf1.get_seasons,
            lambda seasons: DAY if seasons else EMPTY_TTL,
        )

    async def get_season_weekends(self, season: int) -> list[Weekend]:
        async def fetch() -> list[Weekend]:
            raw_weekends = await self._openf1.get_season_weekends(season)
            return [Weekend.from_openf1(raw, Country.from_openf1(raw)) for raw in raw_weekends]

        return await self._cached(
            f"weekends:{season}", WEEKENDS, fetch,
            lambda weekends: self._season_ttl(season) if weekends else EMPTY_TTL,
        )

    async def get_weekend_sessions(self, weekend_id: int) -> list[Session]:
        async def fetch() -> list[Session]:
            data = await self._openf1.get_weekend_sessions(weekend_id)
            return [Session.from_openf1(entry) for entry in data]

        def ttl(sessions: list[Session]) -> int:
            if not sessions:
                return EMPTY_TTL
            cutoff = datetime.now(timezone.utc) - timedelta(days=2)
            return WEEK if all(session.start_time < cutoff for session in sessions) else 300

        return await self._cached(f"weekend:{weekend_id}:sessions", SESSIONS, fetch, ttl)

    async def get_session_results(self, session_id: int) -> Result:
        async def fetch() -> Result:
            raw_classifications = await self._openf1.get_classifications(session_id)
            classifications: list[Classification] = []
            for raw in raw_classifications:
                classifications.append(
                    Classification.from_openf1(raw, classifications[-1] if classifications else None)
                )
            return Result(session_id=session_id, classifications=classifications)

        return await self._cached(
            f"session:{session_id}", RESULT, fetch,
            lambda result: DAY if result.classifications else EMPTY_TTL,
        )

    async def get_season_drivers(self, season: int, driver_id: int) -> Driver:
        async def fetch() -> Driver:
            first_weekend_id = await self._openf1.get_first_weekend_id(season)
            driver_data = await self._openf1.get_season_driver(first_weekend_id, driver_id)
            return Driver.from_openf1(driver_data)

        return await self._cached(f"season:{season}:drivers:{driver_id}", DRIVER, fetch, DAY)

    async def get_driver_standings(self, season: int) -> DriverStandings:
        async def fetch() -> DriverStandings:
            latest_session_id = await self._openf1.get_latest_points_session_id(season)
            raw_standings = await self._openf1.get_driver_standings(latest_session_id)
            return DriverStandings(
                season=season,
                standings=[DriverStanding.from_openf1(raw) for raw in raw_standings],
            )

        return await self._cached(
            f"driver-standings:{season}", DRIVER_STANDINGS, fetch,
            lambda result: self._season_ttl(season) if result.standings else EMPTY_TTL,
        )

    async def get_season_team_standings(self, season: int) -> TeamStandings:
        async def fetch() -> TeamStandings:
            weekends = await self.get_season_weekends(season)
            now = datetime.now(timezone.utc)
            entry: Session | None = None
            for weekend in sorted(weekends, key=lambda item: item.date_start, reverse=True):
                if weekend.cancelled or weekend.date_start > now:
                    continue

                sessions = await self.get_weekend_sessions(weekend.id)
                entry = max(
                    (
                        session for session in sessions
                        if session.type == SessionType.GRAND_PRIX and session.start_time <= now
                    ),
                    key=lambda session: session.start_time,
                    default=None,
                )
                if entry is not None:
                    break

            if entry is None:
                raise ValueError(
                    f"Cannot retrieve team standings for season {season}: "
                    "no Grand Prix session has started in a non-cancelled weekend."
                )
            data = await self._openf1.get_season_team_standings(entry.id)
            return TeamStandings(
                season=season,
                standings=[TeamStanding.from_openf1(raw) for raw in data],
            )

        return await self._cached(
            f"season:{season}:team_standings", TEAM_STANDINGS, fetch,
            lambda result: self._season_ttl(season) if result.standings else EMPTY_TTL,
        )

    async def get_session_starting_grid(self, weekend_id: int) -> list[StartingGrid]:
        async def fetch() -> list[StartingGrid]:
            sessions, data = await gather(
                self.get_weekend_sessions(weekend_id),
                self._openf1.get_session_starting_grid(weekend_id),
            )
            grids: list[StartingGrid] = []
            for session in sessions:
                if session.type not in (SessionType.QUALIFYING, SessionType.SPRINT_QUALIFYING):
                    continue

                positions = [
                    StartingPosition(position=raw["position"], driver_id=raw["driver_number"])
                    for raw in data
                    if raw["session_key"] == session.id and raw["meeting_key"] == weekend_id
                ]
                positions.sort(key=lambda entry: entry.position)
                grids.append(
                    StartingGrid(
                        positions=positions,
                        weekend_id=weekend_id,
                        session_type=session.type,
                        session_id=session.id,
                    )
                )
            return grids

        return await self._cached(
            f"weekend:{weekend_id}:starting_grid", STARTING_GRIDS, fetch,
            lambda grids: DAY if grids and all(grid.positions for grid in grids) else EMPTY_TTL,
        )
