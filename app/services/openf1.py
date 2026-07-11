from base64 import b64encode

from aiolimiter import AsyncLimiter
from httpx import AsyncClient, Response


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
        self._per_second = AsyncLimiter(3, 1)
        self._per_minute = AsyncLimiter(30, 60)

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

        weekends = await self._call_json(f"{self.API_URL}/meetings?year={season}")

        if not isinstance(weekends, list):
            raise ValueError("Unexpected data format from OpenF1 API")

        for raw_weekend in weekends:
            flag_url = raw_weekend["country_flag"]
            flag_data = b64encode(await self._call_content(flag_url)).decode("utf-8")
            raw_weekend["country_flag"] = flag_data
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

    async def get_flag(self, flag_url: str) -> str:
        response = await self._client.get(flag_url)
        response.raise_for_status()
        return response.json()

    async def _call_json(self, url: str) -> dict | list:
        return (await self._call(url)).json()

    async def _call_content(self, url: str) -> bytes:
        return (await self._call(url)).content

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
