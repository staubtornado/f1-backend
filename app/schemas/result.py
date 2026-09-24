from pydantic import BaseModel

from app.schemas.classification import Classification


class Result(BaseModel):
    """Classifications for one session in upstream order."""

    session_id: int
    classifications: list[Classification]
