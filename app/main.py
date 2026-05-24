from contextlib import asynccontextmanager
from os import environ

from fastapi import FastAPI
from httpx import AsyncClient
from redis.asyncio import Redis

from app.api.routes import router
from app.services.apicountries import ApiCountries
from app.services.f1 import F1Service
from app.services.openf1 import OpenF1

REDIS_HOST = environ.get("REDIS_HOST", "127.0.0.1")


@asynccontextmanager
async def lifespan(application: FastAPI):
    session = AsyncClient()
    redis = Redis(host=REDIS_HOST)

    openf1 = OpenF1(session)
    apicountries = ApiCountries(session)

    application.state.f1 = F1Service(openf1, apicountries)
    application.state.redis = redis

    yield

    await session.aclose()
    await redis.aclose()


app = FastAPI(lifespan=lifespan)
app.include_router(router=router)
