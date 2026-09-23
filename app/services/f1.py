from asyncio import gather
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import TypeVar

from fastapi import HTTPException
from pydantic import TypeAdapter
from redis.asyncio import Redis

from app.schemas.classification import Classification
from app.schemas.country import Country
from app.schemas.driver import Driver
from app.schemas.driver_standing import DriverStanding
from app.schemas.driver_standings import DriverStandings
from app.schemas.result import Result
from app.schemas.session import Session
from app.schemas.session_type import SessionType
from app.schemas.starting_grid import StartingGrid
from app.schemas.starting_positon import StartingPosition
from app.schemas.team_standing import TeamStanding
from app.schemas.team_standings import TeamStandings
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
        """
        Initialize the service and share its Redis cache with the OpenF1 client.

        :param openf1: Client used to retrieve upstream data.
        :param redis: Shared Redis connection managed by the caller.
        """
        self._openf1 = openf1
        self._cache = RedisCache(redis)
        self._openf1.set_cache(self._cache)

    async def get_seasons(self) -> list[int]:
        """
        Retrieve available seasons and cache them for one day.

        :return: Ascending list of season years. Empty lists are cached for 30 seconds.
        """
        cache_key = "seasons"

        return await self._cached(
            cache_key,
            SEASONS,
            self._openf1.get_seasons,
            lambda seasons: DAY if seasons else EMPTY_TTL,
        )

    async def get_season_weekends(self, season: int) -> list[Weekend]:
        """
        Retrieve race weekends with country metadata and base64-encoded flags.

        :param season: The season year.
        :return: Weekends cached by season age, or an empty list cached for 30 seconds.
        """
        cache_key = f"weekends:{season}"

        async def fetch() -> list[Weekend]:
            raw_weekends: list[dict] = await self._openf1.get_season_weekends(season)
            weekends: list[Weekend] = []
            for raw in raw_weekends:
                country = Country.from_openf1(raw)
                weekend = Weekend.from_openf1(raw, country)
                weekends.append(weekend)
            return weekends

        return await self._cached(
            cache_key,
            WEEKENDS,
            fetch,
            lambda weekends: self._season_ttl(season) if weekends else EMPTY_TTL,
        )

    async def get_weekend_sessions(self, weekend_id: int) -> list[Session]:
        """
        Retrieve sessions and cache recent schedules for five minutes.

        Schedules whose sessions all started over two days ago are cached for a week.

        :param weekend_id: The OpenF1 meeting key.
        :return: Sessions for the weekend. Empty lists are cached for 30 seconds.
        """
        cache_key = f"weekend:{weekend_id}:sessions"

        async def fetch() -> list[Session]:
            data: list[dict] = await self._openf1.get_weekend_sessions(weekend_id)
            return [Session.from_openf1(entry) for entry in data]

        def ttl(sessions: list[Session]) -> int:
            if not sessions:
                return EMPTY_TTL

            cutoff = datetime.now(timezone.utc) - timedelta(days=2)
            return WEEK if all(session.start_time < cutoff for session in sessions) else 300

        return await self._cached(
            cache_key,
            SESSIONS,
            fetch,
            ttl,
        )

    async def get_session_results(self, session_id: int) -> Result:
        """
        Retrieve session classifications and cache populated results for one day.

        :param session_id: The OpenF1 session key.
        :return: Session results. Empty classifications are cached for 30 seconds.
        """
        cache_key = f"session:{session_id}"

        async def fetch() -> Result:
            raw_classifications: list[dict] = await self._openf1.get_classifications(session_id)
            classifications: list[Classification] = []
            for raw in raw_classifications:
                front_classification = classifications[-1] if classifications else None
                classification = Classification.from_openf1(raw, front_classification)
                classifications.append(classification)

            result = Result(session_id=session_id, classifications=classifications)
            return result

        return await self._cached(
            cache_key,
            RESULT,
            fetch,
            lambda result: DAY if result.classifications else EMPTY_TTL,
        )

    async def get_season_drivers(self, season: int, driver_id: int) -> Driver:
        """
        Retrieve a driver from the season and cache the profile for one day.

        The first weekend is checked before searching the remaining season data.

        :param season: The season year.
        :param driver_id: The driver's racing number.
        :return: Driver profile with an empty portrait string if no image URL exists.
        :raises HTTPException: HTTP 404 if the season has no weekends or the driver is absent.
        """
        cache_key = f"season:{season}:drivers:{driver_id}"

        async def fetch() -> Driver:
            first_weekend_id = await self._openf1.get_first_weekend_id(season)
            if first_weekend_id is None:
                raise HTTPException(status_code=404, detail=f"No weekends found for season {season}.")

            driver_data: dict | None = await self._openf1.get_season_driver(
                first_weekend_id,
                driver_id,
                season=season,
            )
            if driver_data is None:
                raise HTTPException(status_code=404, detail=f"Driver {driver_id} not found in season {season}.")

            driver = Driver.from_openf1(driver_data)
            return driver

        return await self._cached(
            cache_key,
            DRIVER,
            fetch,
            DAY,
        )

    async def get_driver_standings(self, season: int) -> DriverStandings:
        """
        Retrieve driver standings from the latest started Race or Sprint session.

        :param season: The season year.
        :return: Standings cached by season age, or empty standings cached for 30 seconds.
        :raises ValueError: If no eligible session has started in the season.
        """
        cache_key = f"driver-standings:{season}"

        async def fetch() -> DriverStandings:
            latest_session_id = await self._openf1.get_latest_points_session_id(season)
            raw_standings: list[dict] = await self._openf1.get_driver_standings(latest_session_id)
            standings = [DriverStanding.from_openf1(raw) for raw in raw_standings]

            result = DriverStandings(season=season, standings=standings)
            return result

        return await self._cached(
            cache_key,
            DRIVER_STANDINGS,
            fetch,
            lambda result: self._season_ttl(season) if result.standings else EMPTY_TTL,
        )

    async def get_season_team_standings(self, season: int) -> TeamStandings:
        """
        Retrieve team standings from the latest started Grand Prix in a valid weekend.

        :param season: The season year.
        :return: Standings cached by season age, or empty standings cached for 30 seconds.
        :raises ValueError: If no Grand Prix has started in a non-cancelled weekend.
        """
        cache_key = f"season:{season}:team_standings"

        async def fetch() -> TeamStandings:
            weekends: list[Weekend] = await self.get_season_weekends(season)
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

            data: list[dict] = await self._openf1.get_season_team_standings(entry.id)
            standings: list[TeamStanding] = []
            for raw in data:
                standings.append(TeamStanding.from_openf1(raw))

            result = TeamStandings(season=season, standings=standings)
            return result

        return await self._cached(
            cache_key,
            TEAM_STANDINGS,
            fetch,
            lambda result: self._season_ttl(season) if result.standings else EMPTY_TTL,
        )

    async def get_session_starting_grid(self, weekend_id: int) -> list[StartingGrid]:
        """
        Retrieve starting grids for qualifying and sprint qualifying sessions.

        Positions are sorted. Populated grids are cached for one day; empty lists
        or grids containing an empty positions list are cached for 30 seconds.

        :param weekend_id: The OpenF1 meeting key.
        :return: Starting grids associated with the weekend's qualifying sessions.
        """
        cache_key = f"weekend:{weekend_id}:starting_grid"

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
                    StartingPosition(
                        position=raw["position"],
                        driver_id=raw["driver_number"],
                    )
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
            cache_key,
            STARTING_GRIDS,
            fetch,
            lambda grids: DAY if grids and all(grid.positions for grid in grids) else EMPTY_TTL,
        )

    async def _cached(
            self,
            key: str,
            adapter: TypeAdapter[T],
            fetch: Callable[[], Awaitable[T]],
            ttl: int | Callable[[T], int],
    ) -> T:
        """
        Read a cached value or load and serialize it as a single JSON document.

        The v2 key prefix separates these values from the former nested JSON format.
        Concurrent misses for the same key share a loader within this worker.

        :param key: Cache key without the version prefix.
        :param adapter: Serializer and validator for the response type.
        :param fetch: Async callback used when the cache has no value.
        :param ttl: Lifetime in seconds, or a callback deriving it from the loaded value.
        :return: Validated value from Redis or the loader.
        """
        async def load() -> tuple[bytes, int]:
            result = await fetch()
            content = adapter.dump_json(result)
            ex = ttl if isinstance(ttl, int) else ttl(result)
            return content, ex

        cache_key = f"f1:v2:{key}"
        data = await self._cache.get_or_load(cache_key, load)
        return adapter.validate_json(data)

    @staticmethod
    def _season_ttl(season: int) -> int:
        """
        Determine the cache lifetime from the season year.

        :param season: The season year, compared with the current UTC year.
        :return: One week for past seasons, otherwise one hour.
        """
        current_year = datetime.now(timezone.utc).year
        return WEEK if season < current_year else 60 * 60
