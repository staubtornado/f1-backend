from pydantic import BaseModel

from app.schemas.classification import Classification


class Result(BaseModel):
    session_id: int
    classifications: list[Classification]
