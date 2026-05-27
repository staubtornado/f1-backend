from datetime import datetime, timedelta
from typing import Self

from pydantic import BaseModel

from app.schemas.country import Country


class Weekend(BaseModel):
    name: str
    id: int
    country: Country | None
    circuit_id: int
    date_start: datetime
    date_end: datetime
    gmt_offset: timedelta
    cancelled: bool

    @classmethod
    def from_openf1(cls, data: dict, country: Country | None) -> Self:
        return cls(
            id=data["meeting_key"],
            name=data["meeting_name"],
            country=country,
            circuit_id=data["circuit_key"],
            date_start=data["date_start"],
            date_end=data["date_end"],
            gmt_offset=data["gmt_offset"],
            cancelled=data["is_cancelled"],
        )
