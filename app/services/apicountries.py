from base64 import b64encode
from typing import Any

from aiolimiter import AsyncLimiter
from httpx import AsyncClient


class ApiCountries:
    """Client for the REST Countries API and flagcdn.com flag resources.

    Requests are rate-limited to 2 per second to avoid triggering
    undocumented upstream limits.

    :param client: Shared async HTTP client instance.
    """

    API_URL = "https://www.apicountries.com/alpha"

    def __init__(self, client: AsyncClient) -> None:
        self._client = client
        self._per_second = AsyncLimiter(2, 1)

    async def get_country(self, alpha3_code: str) -> tuple[dict, str]:
        """Fetch country metadata and SVG flag for a given ISO 3166-1 alpha-3 code.

        Performs two rate-limited HTTP requests: one to the REST Countries API
        for metadata, and one to flagcdn.com for the SVG flag image.

        :param alpha3_code: ISO 3166-1 alpha-3 country code (e.g. ``"BEL"``).
        :returns: Tuple of the raw API response dict and a base64-encoded SVG flag string.
        :raises httpx.HTTPStatusError: If either upstream request returns a non-2xx status.
        """
        async with self._per_second:
            response = await self._client.get(f"{self.API_URL}/{alpha3_code}")
            response.raise_for_status()

        data: dict[str, Any] = response.json()
        flag_base64 = await self._get_country_flag(data["alpha2Code"])
        return data, flag_base64

    async def _get_country_flag(self, alpha2_code: str) -> str:
        """Download the SVG flag for a given ISO 3166-1 alpha-2 code.

        Returns the flag as a base64-encoded string. The request is rate-limited
        together ``get_country`` via a shared 2 req/s limiter.

        :param alpha2_code: ISO 3166-1 alpha-2 country code (e.g. ``"BE"``).
        :returns: Base64-encoded SVG content as a UTF-8 string.
        :raises httpx.HTTPStatusError: If the flagcdn.com request returns a non-2xx status.
        """
        alpha2_code = alpha2_code.lower()
        async with self._per_second:
            response = await self._client.get(f"https://flagcdn.com/{alpha2_code}.svg")
            response.raise_for_status()
        return b64encode(response.content).decode("utf-8")