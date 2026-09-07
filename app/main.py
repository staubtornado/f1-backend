from contextlib import asynccontextmanager
from os import environ

from fastapi import FastAPI, Request, Response
from httpx import AsyncClient, HTTPStatusError
from redis.asyncio import Redis

from app.api.routes import router
from app.services.f1 import F1Service
from app.services.openf1 import OpenF1

REDIS_HOST = environ.get("REDIS_HOST", "127.0.0.1")


@asynccontextmanager
async def lifespan(application: FastAPI):
    session = AsyncClient()
    redis = Redis(host=REDIS_HOST)

    openf1 = OpenF1(session)

    application.state.f1 = F1Service(openf1, redis)

    yield

    await session.aclose()
    await redis.aclose()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(HTTPStatusError)
async def openf1_http_error_handler(
    _request: Request,
    exception: HTTPStatusError,
) -> Response:
    """Forward an OpenF1 HTTP error without replacing its status or body."""
    upstream_response = exception.response
    content_type = upstream_response.headers.get("content-type")
    headers = {"content-type": content_type} if content_type else None

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=headers,
    )


app.include_router(router=router)
