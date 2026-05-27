from base64 import b64encode

from aiolimiter import AsyncLimiter
from httpx import AsyncClient


class ApiCountries:
    """Client for the REST Countries API and flagcdn.com flag resources.

    Requests are rate-limited to 2 per second to avoid triggering
    undocumented upstream limits.

    :param client: Shared async HTTP client instance.
    """

    API_URL = "https://restcountries.com/v3.1/alpha"

    def __init__(self, client: AsyncClient) -> None:
        self._client = client
        self._per_second = AsyncLimiter(2, 1)

    async def get_country(self, country_code: str) -> tuple[dict, str]:
        """Fetch country metadata and SVG flag for a given ISO 3166-1 alpha-3 code.

        Performs two rate-limited HTTP requests: one to the REST Countries API
        for metadata, and one to flagcdn.com for the SVG flag image.

        :param country_code: Country code. Should follow cca2, ccn3, cca3, or cioc
        :returns: Tuple of the raw API response dict and a base64-encoded SVG flag string.
        :raises httpx.HTTPStatusError: If either upstream request returns a non-2xx status.
        """
        async with self._per_second:
            response = await self._client.get(f"{self.API_URL}/{country_code}")
            response.raise_for_status()

        data: list[dict] = response.json()
        flag_base64 = await self._get_country_flag(data[0]["flags"]["svg"])
        return data[0], flag_base64

    async def _get_country_flag(self, url: str) -> str:
        """Download the SVG flag for a given ISO 3166-1 alpha-2 code.

        Returns the flag as a base64-encoded string. The request is rate-limited
        together ``get_country`` via a shared 2 req/s limiter.

        :param url: URL of the flag image.
        :returns: Base64-encoded SVG content as a UTF-8 string.
        :raises httpx.HTTPStatusError: If the flagcdn.com request returns a non-2xx status.
        """
        async with self._per_second:
            response = await self._client.get(url)
            response.raise_for_status()
        return b64encode(response.content).decode("utf-8")