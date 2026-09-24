"""Create the FastAPI application, shared clients and upstream error handler."""

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
    """
    Create shared clients and install the F1 service for the application lifespan.

    After normal completion of the yield, close the HTTP and Redis clients.
    The Redis hostname comes from ``REDIS_HOST`` (default: ``127.0.0.1``).

    :param application: FastAPI application receiving ``state.f1``.
    :yields: None while the application serves requests.
    """
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
    """
    Forward an upstream HTTP error without replacing its status or body.

    This also covers failed image downloads. Only the upstream Content-Type
    header is copied; other headers such as Retry-After are not forwarded.

    :param _request: Request that triggered the error; unused by this handler.
    :param exception: HTTP status error containing the upstream response.
    :return: Response preserving the upstream status, body and Content-Type.
    """
    upstream_response = exception.response
    content_type = upstream_response.headers.get("content-type")
    headers = {"content-type": content_type} if content_type else None

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=headers,
    )


app.include_router(router=router)
