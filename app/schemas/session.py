from datetime import datetime
from typing import Self

from pydantic import BaseModel

from app.schemas.session_type import SessionType


class Session(BaseModel):
    id: int
    type: SessionType
    weekend_id: int
    start_time: datetime

    @classmethod
    def from_openf1(cls, data: dict) -> Self:
        session_type_mapping = {
            "Qualifying": SessionType.QUALIFYING,
            "Practice 1": SessionType.PRACTICE_ONE,
            "Practice 2": SessionType.PRACTICE_TWO,
            "Practice 3": SessionType.PRACTICE_THREE,
            "Sprint": SessionType.SPRINT,
            "Sprint Qualifying": SessionType.SPRINT_QUALIFYING,
            "Race": SessionType.GRAND_PRIX,
        }

        return cls(
            id=data["session_key"],
            type=session_type_mapping[data["session_name"]],
            weekend_id=data["meeting_key"],
            start_time=data["date_start"],
        )