from httpx import AsyncClient


class OpenF1:
    API_URL = "https://api.openf1.org/v1"

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def get_sessions(self, year: int) -> dict:
        response = await self._client.get(f"{self.API_URL}/sessions?year={year}")
        response.raise_for_status()
        return response.json()
