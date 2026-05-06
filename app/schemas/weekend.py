from datetime import datetime, timedelta
from typing import Self

from pydantic import BaseModel


class Weekend(BaseModel):
    name: str
    id: int
    country_code: str
    circuit_id: int
    date_start: datetime
    date_end: datetime
    gmt_offset: timedelta
    cancelled: bool

    @classmethod
    def from_openf1(cls, data: dict) -> Self:
        return cls(
            id=data["meeting_key"],
            name=data["meeting_name"],
            country_code=data["country_code"],
            circuit_id=data["circuit_key"],
            date_start=data["date_start"],
            date_end=data["date_end"],
            gmt_offset=data["gmt_offset"],
            cancelled=data["is_cancelled"],
        )
