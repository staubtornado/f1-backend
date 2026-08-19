from datetime import datetime
from json import loads, dumps

from redis.asyncio import Redis

from app.schemas.classification import Classification
from app.schemas.country import Country
from app.schemas.result import Result
from app.schemas.session import Session
from app.schemas.weekend import Weekend
from app.services.openf1 import OpenF1


class F1Service:
    def __init__(self, openf1: OpenF1, redis: Redis) -> None:
        self._openf1 = openf1
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
            country = Country.from_openf1(raw)
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

    async def get_session_results(self, session_id: int) -> Result:
        cache_key = f"session:{session_id}"

        if cached := await self._redis.get(cache_key):
            return Result.model_validate_json(cached)

        raw_classifications: list[dict] = await self._openf1.get_classifications(session_id)
        classifications: list[Classification] = []

        for i, raw in enumerate(raw_classifications):
            try:
                classifications.append(Classification.from_openf1(raw, classifications[i - 1] if i > 0 else None))
            except ValueError:
                pass

        result = Result(session_id=session_id, classifications=classifications)

        await self._redis.set(
            cache_key,
            result.model_dump_json(),
            ex=60 * 60 * 24,
        )
        return result
