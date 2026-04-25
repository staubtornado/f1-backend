from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import AsyncClient

from app.services.openf1 import OpenF1


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with AsyncClient() as session:
        application.state.openf1 = OpenF1(session)
        yield


app = FastAPI(lifespan=lifespan)
