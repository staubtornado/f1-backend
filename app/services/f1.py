from redis.asyncio import Redis

from app.schemas.country import Country
from app.schemas.session import Session
from app.schemas.weekend import Weekend
from app.services.apicountries import ApiCountries
from app.services.openf1 import OpenF1


class F1Service:
    def __init__(self, openf1: OpenF1, countries: ApiCountries, redis: Redis) -> None:
        self._openf1 = openf1
        self._countries = countries
        self._redis = redis

    async def get_seasons(self) -> list[int]:
        return await self._openf1.get_seasons()

    async def get_season_weekends(self, season: int) -> list[Weekend]:
        """
        Fetch all race weekends for a given season, enriched with country metadata and flags.

        For each weekend, two additional HTTP requests are made to resolve country data.
        Countries are not deduplicated — use with caution for large seasons.

        :param season: Formula 1-season year (e.g. ``2024``).
        :returns: List of `Weekend` instances with fully populated `Country` data.
        :raises httpx.HTTPStatusError: If any upstream request returns a non-2xx status.
        """
        raw_weekends: list[dict] = await self._openf1.get_season_weekends(season)

        return [
            Weekend.from_openf1(
                raw,
                country=Country.from_api_countries(
                    *await self._get_country(raw["country_code"])
                ),
            )
            for raw in raw_weekends
        ]

    async def get_weekend_sessions(self, weekend_id: int) -> list[Session]:
        data: list[dict] = await self._openf1.get_weekend_sessions(weekend_id)
        return [Session.from_openf1(entry) for entry in data]

    async def _get_country(self, alpha3_code: str) -> Country:
        cache_key = f"country:{alpha3_code}"

        if cached := await self._redis.get(cache_key):
            return Country.model_validate(cached)

        country_data, flag_base64 = await self._countries.get_country(alpha3_code)
        country = Country.from_api_countries(country_data, flag_base64)

        await self._redis.set(cache_key, country.model_dump(), ttl=60 * 60 * 24 * 7)
        return country