from httpx import AsyncClient

from app.schemas.session import Session


class OpenF1:
    API_URL = "https://api.openf1.org/v1"

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def get_seasons(self) -> list[int]:
        data: list[dict] = await self._call(f"{self.API_URL}/sessions")
        years: set[int] = set()

        for entry in data:
            years.add(entry["year"])
        return sorted(years)

    async def get_season_weekends(self, season: int) -> list[dict]:
        return await self._call(f"{self.API_URL}/meetings?year={season}")

    async def get_weekend_sessions(self, weekend_id: int) -> list[dict]:
        return await self._call(f"{self.API_URL}/sessions?meeting_key={weekend_id}")

    async def _call(self, url: str) -> dict | list:
        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()
