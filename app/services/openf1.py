from httpx import AsyncClient

from app.schemas.session import Session
from app.schemas.weekend import Weekend


class OpenF1:
    API_URL = "https://api.openf1.org/v1"

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def get_seasons(self) -> list[int]:
        response = await self._client.get(f"{self.API_URL}/sessions")
        response.raise_for_status()

        data: list[dict] = response.json()
        years: set[int] = set()

        for entry in data:
            years.add(entry["year"])
        return sorted(years)

    async def get_season_weekends(self, season: int) -> list[Weekend]:
        response = await self._client.get(f"{self.API_URL}/meetings?year={season}")
        response.raise_for_status()

        data: list[dict] = response.json()
        return [Weekend.from_openf1(entry) for entry in data]

    async def get_weekend_sessions(self, weekend_id: int) -> list[Session]:
        response = await self._client.get(f"{self.API_URL}/sessions?meeting_key={weekend_id}")
        response.raise_for_status()

        data: list[dict] = response.json()
        return [Session.from_openf1(entry) for entry in data]
