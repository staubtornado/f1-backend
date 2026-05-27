from datetime import datetime
from json import loads, dumps

from httpx import HTTPStatusError
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
        cache_key = "seasons"
        if cached := await self._redis.get(cache_key):
            return loads(cached)

        seasons = await self._openf1.get_seasons()
        await self._redis.set(cache_key, dumps(seasons), ex=60 * 60 * 24)
        return seasons

    async def get_season_weekends(self, season: int) -> list[Weekend]:
        cache_key = f"weekends:{season}"

        if cached := await self._redis.get(cache_key):
            return [Weekend.model_validate_json(entry) for entry in loads(cached)]

        raw_weekends: list[dict] = await self._openf1.get_season_weekends(season)
        weekends = []
        for raw in raw_weekends:
            try:
                country = await self._get_country(raw["country_code"])
            except HTTPStatusError:
                country = None
            weekend = Weekend.from_openf1(raw, country)
            weekends.append(weekend)

        current_year = datetime.now().year
        ex = 60 * 60 * 24 * 7 if season < current_year else 60 * 60

        await self._redis.set(
            cache_key,
            dumps([w.model_dump_json() for w in weekends]),
            ex=ex,
        )
        return weekends

    async def get_weekend_sessions(self, weekend_id: int) -> list[Session]:
        data: list[dict] = await self._openf1.get_weekend_sessions(weekend_id)
        return [Session.from_openf1(entry) for entry in data]

    async def _get_country(self, alpha3_code: str) -> Country:
        cache_key = f"country:{alpha3_code}"

        if cached := await self._redis.get(cache_key):
            return Country.model_validate_json(cached)

        country_data, flag_base64 = await self._countries.get_country(alpha3_code)
        country = Country.from_api_countries(country_data, flag_base64)

        await self._redis.set(cache_key, country.model_dump_json(), ex=60 * 60 * 24 * 7)
        return country
