from asyncio import Lock, Semaphore, gather
from base64 import b64encode
from collections.abc import Awaitable, Callable
from hashlib import sha256
from json import dumps, loads
from weakref import WeakValueDictionary

from aiolimiter import AsyncLimiter
from httpx import AsyncClient, Response
from datetime import datetime, timezone
from redis.asyncio import Redis


class RedisCache:
    """Cache serialized values and coalesce concurrent misses within a worker."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._locks: WeakValueDictionary[str, Lock] = WeakValueDictionary()

    async def get_or_load(
            self,
            key: str,
            load: Callable[[], Awaitable[tuple[bytes, int]]],
    ) -> bytes | str:
        cached = await self._redis.get(key)
        if cached is not None:
            return cached

        # Keep the lock alive until all callers have left, without retaining
        # one lock forever for every session, driver or image ever requested.
        lock = self._locks.setdefault(key, Lock())
        async with lock:
            cached = await self._redis.get(key)
            if cached is not None:
                return cached
            value, ttl = await load()
            await self._redis.set(key, value, ex=ttl)
            return value


class OpenF1:
    """
    Client for the OpenF1 REST API.

    Wraps HTTP communication and rate limiting against the public
    OpenF1 API (https://api.openf1.org/v1). Rate limits are enforced
    at 3 requests/second and 30 requests/minute.

    :param client: Shared async HTTP client instance. Lifecycle management
        (creation and teardown) is the caller's responsibility.
    """

    API_URL = "https://api.openf1.org/v1"

    def __init__(self, client: AsyncClient) -> None:
        self._client = client
        self._cache: RedisCache | None = None
        self._image_downloads = Semaphore(8)
        self._per_second = AsyncLimiter(3, 1)
        self._per_minute = AsyncLimiter(30, 60)

    def set_cache(self, cache: RedisCache) -> None:
        self._cache = cache

    async def _get_meetings(self, season: int) -> list[dict]:
        ttl = 60 * 60 * 24 * 7 if season < datetime.now(timezone.utc).year else 60 * 60
        data = await self._call_json(f"{self.API_URL}/meetings?year={season}", ttl=ttl)
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")
        return data

    async def get_first_weekend_id(self, season: int) -> int:
        # Driver lookups need only the meeting id, not every country's flag.
        return (await self._get_meetings(season))[0]["meeting_key"]

    async def get_seasons(self) -> list[int]:
        """
        Fetch all available F1 seasons as a sorted list of years.

        Retrieves all sessions from the API and deduplicates by year.

        :return: Ascending list of season years, e.g. ``[2023, 2024, 2025]``.
        :raises httpx.HTTPStatusError: If the upstream request returns a non-2xx status.
        """
        data: list[dict] | dict = await self._call_json(f"{self.API_URL}/sessions")

        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")

        years: set[int] = set()

        for entry in data:
            years.add(entry["year"])
        return sorted(years)

    async def get_season_weekends(self, season: int) -> list[dict]:
        """
        Fetch all race weekends for a given season.

        :param season: The season year, e.g. ``2024``.
        :return: List of meeting objects as returned by the OpenF1 API.
        :raises httpx.HTTPStatusError: If the upstream request returns a non-2xx status.
        """

        weekends = await self._get_meetings(season)
        flag_urls = list(dict.fromkeys(raw["country_flag"] for raw in weekends))
        flags = await gather(*(self._get_image_base64(url) for url in flag_urls))
        flags_by_url = dict(zip(flag_urls, flags))
        for raw_weekend in weekends:
            raw_weekend["country_flag"] = flags_by_url[raw_weekend["country_flag"]]
        return weekends

    async def get_weekend_sessions(self, weekend_id: int) -> list[dict]:
        """
        Fetch all sessions for a given race weekend.

        Sessions include practice, qualifying, sprint, and race.

        :param weekend_id: The id of the target weekend is obtainable via ``get_season_weekends``.
        :return: List of session objects as returned by the OpenF1 API.
        :raises httpx.HTTPStatusError: If the upstream request returns a non-2xx status.
        """
        data = await self._call_json(f"{self.API_URL}/sessions?meeting_key={weekend_id}")
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")
        return data

    async def get_classifications(self, session_id: int) -> list[dict]:
        """
        Fetch the results for a given session.

        :param session_id: The id of the target session is obtainable via ``get_weekend_sessions``.
        :return: List of session result objects as returned by the OpenF1 API.
        :raises httpx.HTTPStatusError: If the upstream request returns a non-2xx status.
        """
        data = await self._call_json(f"{self.API_URL}/session_result?session_key={session_id}")
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")
        return data

    async def get_season_driver(self, weekend_id: int, driver_id: int) -> dict:
        # All drivers of a meeting share one upstream response. Loading a grid
        # of driver cards must not consume one API rate-limit token per card.
        data = await self._call_json(
            f"{self.API_URL}/drivers?meeting_key={weekend_id}", ttl=60 * 60 * 24,
        )
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")

        entry: dict = [raw for raw in data if raw["driver_number"] == driver_id][0]

        portrait_url = entry["headshot_url"]
        portrait_base64 = await self._get_image_base64(portrait_url)
        entry["portrait_base64"] = portrait_base64

        return entry

    async def get_driver_standings(self, session_id: int) -> list[dict]:
        data = await self._call_json(f"{self.API_URL}/championship_drivers?session_key={session_id}")
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")
        return data

    async def get_latest_points_session_id(self, season: int) -> int:
        """
        Return the session_key of the last completed points session of a season.
        This includes both Race and Sprint sessions.
        If the season is still running, it returns the latest session that has already happened.
        """
        data = await self._call_json(f"{self.API_URL}/sessions?year={season}")
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")

        allowed_types = {"Race", "Sprint"}
        valid_sessions: list[tuple] = []

        for entry in data:
            if entry.get("session_type") not in allowed_types:
                continue
            if entry.get("is_cancelled", False):
                continue
            if not entry.get("date_start"):
                continue

            try:
                started_at = datetime.fromisoformat(entry["date_start"].replace("Z", "+00:00"))
            except ValueError:
                continue

            if started_at <= datetime.now(timezone.utc):
                valid_sessions.append((started_at, entry))

        if not valid_sessions:
            raise ValueError(f"No completed Race/Sprint sessions found for season {season}")

        _, latest_session = max(valid_sessions, key=lambda item: item[0])
        return latest_session["session_key"]

    async def get_season_team_standings(self, session_id: int) -> list[dict]:
        data = await self._call_json(f"{self.API_URL}/championship_teams?session_key={session_id}")
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")

        return data

    async def get_session_starting_grid(self, weekend_id: int) -> list[dict]:
        data = await self._call_json(f"{self.API_URL}/starting_grid?meeting_key={weekend_id}")
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")
        return data

    async def _call_json(self, url: str, *, ttl: int = 0) -> dict | list:
        if self._cache is None or not ttl:
            return (await self._call(url)).json()

        async def load() -> tuple[bytes, int]:
            data = (await self._call(url)).json()
            if not isinstance(data, list):
                raise ValueError("Unexpected data format from OpenF1 API")
            return dumps(data, separators=(",", ":")).encode(), ttl if data else 30

        key = f"openf1:json:v1:{sha256(url.encode()).hexdigest()}"
        return loads(await self._cache.get_or_load(key, load))

    async def _get_image_base64(self, url: str) -> str:
        async def load() -> tuple[bytes, int]:
            return b64encode(await self._call_content(url)), 60 * 60 * 24 * 7

        if self._cache is None:
            content, _ = await load()
        else:
            key = f"openf1:image:v1:{sha256(url.encode()).hexdigest()}"
            content = await self._cache.get_or_load(key, load)
        return content.decode("ascii") if isinstance(content, bytes) else content

    async def _call_content(self, url: str) -> bytes:
        async with self._image_downloads:
            # CDN downloads do not count towards the OpenF1 API quota.
            if url.startswith(f"{self.API_URL}/"):
                return (await self._call(url)).content
            response = await self._client.get(url)
            response.raise_for_status()
            return response.content

    async def _call(self, url: str) -> Response:
        """
        Execute a rate-limited GET request.

        Blocks the calling coroutine until both the per-second and
        per-minute limiters have a token available.

        :param url: Full request URL.
        :return: Deserialized JSON response body.
        :raises httpx.HTTPStatusError: If the upstream request returns a non-2xx status.
        """
        async with self._per_second, self._per_minute:
            response = await self._client.get(url)
            response.raise_for_status()
            return response
