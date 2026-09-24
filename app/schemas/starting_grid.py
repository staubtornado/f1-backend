from pydantic import BaseModel

from app.schemas.session_type import SessionType
from app.schemas.starting_positon import StartingPosition


class StartingGrid(BaseModel):
    """Sorted starting positions associated with a weekend's qualifying session."""

    positions: list[StartingPosition]
    weekend_id: int
    session_type: SessionType
    session_id: int
