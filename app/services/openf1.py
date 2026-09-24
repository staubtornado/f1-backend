"""Retrieve OpenF1 data and images with request pacing and optional Redis caching."""

from asyncio import Lock, Semaphore, gather, sleep
from base64 import b64encode
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from json import dumps, loads
from math import isfinite
from time import monotonic
from weakref import WeakValueDictionary

from aiolimiter import AsyncLimiter
from httpx import AsyncClient, Response
from redis.asyncio import Redis


class RedisCache:
    """Cache serialized values with per-key locks local to this instance."""

    def __init__(self, redis: Redis) -> None:
        """
        Initialize the cache with per-key locks for concurrent misses in this worker.

        Locks are removed once no callers hold a reference to them.

        :param redis: Shared Redis connection managed by the caller.
        """
        self._redis = redis
        self._locks: WeakValueDictionary[str, Lock] = WeakValueDictionary()

    async def get_or_load(
            self,
            key: str,
            load: Callable[[], Awaitable[tuple[bytes, int]]],
    ) -> bytes | str:
        """
        Retrieve a serialized value or load and cache it under a per-key lock.

        The cache is checked again after acquiring the lock. Failed loads are not cached.

        :param key: Redis cache key.
        :param load: Async callback returning the value and its lifetime in seconds.
        :return: Bytes from a fresh load, or bytes/string from Redis depending on
            its decoding configuration.
        """
        cached = await self._redis.get(key)
        if cached is not None:
            return cached

        lock = self._locks.setdefault(key, Lock())
        async with lock:
            cached = await self._redis.get(key)
            if cached is not None:
                return cached

            value, ttl = await load()
            await self._redis.set(key, value, ex=ttl)
            return value


class OpenF1:
    """Fetch raw upstream records and enrich flags and driver portraits."""

    API_URL = "https://api.openf1.org/v1"

    def __init__(self, client: AsyncClient) -> None:
        """
        Initialize the OpenF1 client with request pacing and bounded image downloads.

        API requests are spaced at least 2.1 seconds apart within this client.
        Image downloads allow up to eight concurrent requests.

        :param client: Shared async HTTP client managed by the caller.
        """
        self._client = client
        self._cache: RedisCache | None = None
        self._image_downloads = Semaphore(8)
        self._request_lock = Lock()
        self._retry_at = 0.0
        self._per_second = AsyncLimiter(1, 0.35)
        self._per_minute = AsyncLimiter(1, 2.1)

    def set_cache(self, cache: RedisCache) -> None:
        """
        Attach the cache used for meeting data, driver data and images.

        :param cache: Redis cache shared with the F1 service.
        """
        self._cache = cache

    async def get_seasons(self) -> list[int]:
        """
        Fetch all available F1 seasons as a sorted list of years.

        Retrieves all sessions from the API and deduplicates by year.

        :return: Ascending list of season years, e.g. ``[2023, 2024, 2025]``.
        :raises ValueError: If the API response is not a list.
        :raises httpx.HTTPStatusError: If the upstream request fails after any retries.
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

        Distinct country flags are loaded concurrently and reused from the image cache.

        :param season: The season year, e.g. ``2024``.
        :return: Meeting objects with base64-encoded flags, or empty strings for missing URLs.
        :raises ValueError: If the API response is not a list.
        :raises httpx.HTTPStatusError: If fetching meetings or an image fails.
        """
        weekends: list[dict] = await self._get_meetings(season)
        flag_urls: list[str | None] = list(dict.fromkeys(raw["country_flag"] for raw in weekends))
        flags = await gather(*(self._get_image_base64(url) for url in flag_urls))
        flags_by_url: dict[str | None, str] = dict(zip(flag_urls, flags))

        for raw_weekend in weekends:
            raw_weekend["country_flag"] = flags_by_url[raw_weekend["country_flag"]]
        return weekends

    async def get_first_weekend_id(self, season: int) -> int | None:
        """
        Retrieve the first weekend id in API order without downloading country flags.

        :param season: The season year.
        :return: The first meeting key, or None if the season contains no meetings.
        """
        weekends: list[dict] = await self._get_meetings(season)
        if not weekends:
            return None
        return weekends[0]["meeting_key"]

    async def get_weekend_sessions(self, weekend_id: int) -> list[dict]:
        """
        Fetch all sessions for a given race weekend.

        Sessions include practice, qualifying, sprint, race and testing sessions.

        :param weekend_id: The id of the target weekend is obtainable via ``get_season_weekends``.
        :return: List of session objects as returned by the OpenF1 API.
        :raises ValueError: If the API response is not a list.
        :raises httpx.HTTPStatusError: If the upstream request fails after any retries.
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
        :raises ValueError: If the API response is not a list.
        :raises httpx.HTTPStatusError: If the upstream request fails after any retries.
        """
        data = await self._call_json(f"{self.API_URL}/session_result?session_key={session_id}")
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")
        return data

    async def get_season_driver(
            self,
            weekend_id: int,
            driver_id: int,
            *,
            season: int | None = None,
    ) -> dict | None:
        """
        Retrieve a driver profile and add its base64-encoded portrait.

        All drivers of the initial weekend share one cached API response. If the
        driver is absent and a season is supplied, restrict fallback data to that season.

        :param weekend_id: The meeting key to check first.
        :param driver_id: The driver's racing number.
        :param season: Optional season year used for the fallback search.
        :return: Driver data, or None if absent. Missing portraits use an empty string.
        :raises ValueError: If an API response is not a list.
        :raises httpx.HTTPStatusError: If fetching driver data or the portrait fails.
        """
        data = await self._get_drivers(f"meeting_key={weekend_id}")
        drivers: list[dict] = [raw for raw in data if raw["driver_number"] == driver_id]

        if not drivers and season is not None:
            weekends = await self._get_meetings(season)
            weekend_ids = {raw["meeting_key"] for raw in weekends}
            data = await self._get_drivers(
                f"driver_number={driver_id}",
                ttl=60 * 60,
            )

            drivers = [
                raw for raw in data
                if raw["driver_number"] == driver_id and raw["meeting_key"] in weekend_ids
            ]

        if not drivers:
            return None

        return await self._with_driver_portrait(drivers[0])

    async def get_session_drivers(self, session_id: int) -> list[dict]:
        """
        Retrieve all driver profiles for a session with base64-encoded portraits.

        :param session_id: The OpenF1 session key.
        :return: Driver profiles with an empty portrait string if no image URL exists.
        :raises ValueError: If the API response is not a list.
        :raises httpx.HTTPStatusError: If fetching driver data or a portrait fails.
        """
        drivers = await self._get_drivers(f"session_key={session_id}")
        return list(await gather(*(self._with_driver_portrait(driver) for driver in drivers)))

    async def get_driver_standings(self, session_id: int) -> list[dict]:
        """
        Fetch driver championship standings for a session.

        :param session_id: The OpenF1 session key.
        :return: Driver standings as returned by the API.
        :raises ValueError: If the API response is not a list.
        :raises httpx.HTTPStatusError: If the upstream request fails after any retries.
        """
        data = await self._call_json(f"{self.API_URL}/championship_drivers?session_key={session_id}")
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")
        return data

    async def get_latest_points_session_id(self, season: int) -> int | None:
        """
        Retrieve the latest non-cancelled Race or Sprint session that has started.

        Selection uses the start time; the session does not have to be completed.

        :param season: The season year.
        :return: The latest eligible session key, or None if no eligible session exists.
        :raises ValueError: If the response is not a list.
        :raises httpx.HTTPStatusError: If the upstream request fails after any retries.
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
            return None

        _, latest_session = max(valid_sessions, key=lambda item: item[0])
        return latest_session["session_key"]

    async def get_season_team_standings(self, session_id: int) -> list[dict]:
        """
        Fetch team championship standings for a session.

        :param session_id: The OpenF1 session key.
        :return: Team standings as returned by the API.
        :raises ValueError: If the API response is not a list.
        :raises httpx.HTTPStatusError: If the upstream request fails after any retries.
        """
        data = await self._call_json(f"{self.API_URL}/championship_teams?session_key={session_id}")
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")

        return data

    async def get_session_starting_grid(self, weekend_id: int) -> list[dict]:
        """
        Fetch starting-grid entries for a race weekend.

        :param weekend_id: The OpenF1 meeting key.
        :return: Grid entries as returned by the API, without sorting or grouping.
        :raises ValueError: If the API response is not a list.
        :raises httpx.HTTPStatusError: If the upstream request fails after any retries.
        """
        data = await self._call_json(f"{self.API_URL}/starting_grid?meeting_key={weekend_id}")
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")
        return data

    async def get_grand_prix_session_positions(self, session_id: int) -> list[dict]:
        """
        Fetch position changes for a session without sorting them.

        The session type is not checked; any OpenF1 session key can be supplied.

        :param session_id: The OpenF1 session key.
        :return: Position records in upstream order.
        :raises ValueError: If the API response is not a list.
        :raises httpx.HTTPStatusError: If the upstream request fails after any retries.
        """
        data = await self._call_json(f"{self.API_URL}/position?session_key={session_id}")
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")
        return data

    async def _get_drivers(self, query: str, *, ttl: int = 60 * 60 * 24) -> list[dict]:
        """
        Fetch and validate cached driver data before selecting or enriching profiles.

        :param query: OpenF1 filters, e.g. ``meeting_key=1217`` or ``session_key=9144``.
        :param ttl: Cache lifetime in seconds; empty responses use 30 seconds.
        :return: Driver objects as returned by OpenF1, without portrait downloads.
        :raises ValueError: If the API response is not a list.
        """
        data = await self._call_json(
            f"{self.API_URL}/drivers?{query}",
            ttl=ttl,
        )
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")
        return data

    async def _with_driver_portrait(self, driver: dict) -> dict:
        """
        Copy a driver profile and add its base64-encoded portrait.

        :param driver: Upstream driver record with an optional ``headshot_url``.
        :return: A new dictionary with ``portrait_base64``; missing URLs yield
            an empty string. The input dictionary is not modified.
        :raises httpx.HTTPStatusError: If the portrait download fails.
        """
        portrait = await self._get_image_base64(driver.get("headshot_url"))
        return {**driver, "portrait_base64": portrait}

    async def _get_meetings(self, season: int) -> list[dict]:
        """
        Retrieve meeting data while preserving the original country flag URLs.

        Past seasons are cached for a week, other seasons for an hour and empty lists
        for 30 seconds, provided a cache is attached.

        :param season: The season year.
        :return: Meeting objects as returned by the API.
        :raises ValueError: If the API response is not a list.
        """
        current_year = datetime.now(timezone.utc).year
        ttl = 60 * 60 * 24 * 7 if season < current_year else 60 * 60

        data = await self._call_json(f"{self.API_URL}/meetings?year={season}", ttl=ttl)
        if not isinstance(data, list):
            raise ValueError("Unexpected data format from OpenF1 API")
        return data

    async def _call_json(self, url: str, *, ttl: int = 0) -> dict | list:
        """
        Fetch JSON and optionally cache a list response.

        Cached values are deserialized on each read so callers can modify them safely.
        Empty lists are cached for 30 seconds.

        :param url: Full API request URL.
        :param ttl: Cache lifetime in seconds; zero disables caching for this call.
        :return: Decoded JSON response.
        :raises ValueError: If JSON decoding fails or a cacheable response is not a list.
        :raises httpx.HTTPStatusError: If the upstream request fails after any retries.
        """
        if self._cache is None or not ttl:
            return (await self._call(url)).json()

        async def load() -> tuple[bytes, int]:
            """Fetch a list response and serialize it with its cache lifetime."""
            data = (await self._call(url)).json()
            if not isinstance(data, list):
                raise ValueError("Unexpected data format from OpenF1 API")

            content = dumps(data, separators=(",", ":")).encode()
            ex = ttl if data else 30
            return content, ex

        cache_key = f"openf1:json:v1:{sha256(url.encode()).hexdigest()}"
        cached = await self._cache.get_or_load(cache_key, load)
        return loads(cached)

    async def _get_image_base64(self, url: str | None) -> str:
        """
        Retrieve a base64-encoded image and cache it by URL for one week.

        :param url: Image URL, which may be missing or empty.
        :return: Base64-encoded image, or an empty string when no URL is provided.
        :raises httpx.HTTPStatusError: If the image download fails.
        """
        if not url:
            return ""

        image_url: str = url

        async def load() -> tuple[bytes, int]:
            """Download and encode the image with a one-week cache lifetime."""
            image_data = await self._call_content(image_url)
            return b64encode(image_data), 60 * 60 * 24 * 7

        if self._cache is None:
            content, _ = await load()
        else:
            cache_key = f"openf1:image:v1:{sha256(url.encode()).hexdigest()}"
            content = await self._cache.get_or_load(cache_key, load)

        if isinstance(content, bytes):
            return content.decode("ascii")
        return content

    async def _call_content(self, url: str) -> bytes:
        """
        Download image bytes while limiting concurrent downloads.

        OpenF1 API URLs use the API limiter and retries. External image URLs are
        requested directly without consuming the API quota.

        :param url: Full image URL.
        :return: Raw image bytes.
        :raises httpx.HTTPStatusError: If the image download fails.
        """
        async with self._image_downloads:
            if url.startswith(f"{self.API_URL}/"):
                return (await self._call(url)).content

            response = await self._client.get(url)
            response.raise_for_status()
            return response.content

    async def _call(self, url: str) -> Response:
        """
        Execute a rate-limited GET request with up to two retries on HTTP 429.

        Requests share a lock and cooldown within this client. Each attempt waits
        for both rate limiters. A final HTTP 429 also delays the next request.

        :param url: Full request URL.
        :return: HTTP response.
        :raises httpx.HTTPStatusError: If retries are exhausted or another HTTP error occurs.
        """
        async with self._request_lock:
            attempt = 0
            while True:
                delay = self._retry_at - monotonic()
                if delay > 0:
                    await sleep(delay)

                async with self._per_minute, self._per_second:
                    response = await self._client.get(url)

                if response.status_code == 429:
                    delay = self._get_retry_delay(response, attempt)
                    self._retry_at = monotonic() + delay
                    if attempt < 2:
                        attempt += 1
                        continue

                break

        response.raise_for_status()
        return response

    @staticmethod
    def _get_retry_delay(response: Response, attempt: int) -> float:
        """
        Determine the cooldown from Retry-After or exponential backoff.

        Retry-After may contain seconds or an HTTP date. Missing or invalid values
        fall back to 2, 4 or 8 seconds for the three request attempts.

        :param response: The HTTP 429 response.
        :param attempt: Zero-based index of the failed attempt.
        :return: Non-negative delay in seconds.
        """
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                delay = float(retry_after)
                if isfinite(delay):
                    return max(0.0, delay)
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    delay = (retry_at - datetime.now(timezone.utc)).total_seconds()
                    return max(0.0, delay)
                except (TypeError, ValueError, OverflowError):
                    pass

        return 2.0 ** (attempt + 1)
