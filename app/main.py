from asyncio import run
from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx import AsyncClient

from app.services.openf1 import OpenF1


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncClient() as session:
        app.state.openf1 = OpenF1(session)
        yield


async def main() -> None:
    app = FastAPI(liefespan=lifespan)


if __name__ == "__main__":
    run(main())
