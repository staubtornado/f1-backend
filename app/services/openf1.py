from asyncio import sleep

from httpx import AsyncClient

from app.schemas.race import Race


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
            await sleep(0)
        return sorted(years)

    async def get_season_races(self, season: int) -> list[Race]:
        response = await self._client.get(f"{self.API_URL}/meetings?year={season}")
        response.raise_for_status()

        data: list[dict] = response.json()
        return [Race.from_openf1(entry) for entry in data]
