from datetime import datetime
from typing import Self

from pydantic import BaseModel

from app.schemas.session_type import SessionType


class Session(BaseModel):
    """A session's identifier, normalized type, meeting and start time."""

    id: int
    type: SessionType
    weekend_id: int
    start_time: datetime

    @classmethod
    def from_openf1(cls, data: dict) -> Self:
        """
        Convert an OpenF1 session and normalize its session name.

        :param data: Session record with identifiers, ``session_name`` and ``date_start``.
        :return: Session model, including practice, qualifying, race, sprint or
            one of the three testing days.
        :raises KeyError: If a required field is missing or the session name is
            not present in the explicit mapping.
        :raises pydantic.ValidationError: If the model fields fail validation.
        """
        type_mapping = {
            "Qualifying": SessionType.QUALIFYING,
            "Practice 1": SessionType.PRACTICE_ONE,
            "Practice 2": SessionType.PRACTICE_TWO,
            "Practice 3": SessionType.PRACTICE_THREE,
            "Sprint": SessionType.SPRINT,
            "Sprint Qualifying": SessionType.SPRINT_QUALIFYING,
            "Race": SessionType.GRAND_PRIX,
            "Day 1": SessionType.DAY_1,
            "Day 2": SessionType.DAY_2,
            "Day 3": SessionType.DAY_3,
        }

        return cls(
            id=data["session_key"],
            type=type_mapping[data["session_name"]],
            weekend_id=data["meeting_key"],
            start_time=data["date_start"],
        )
