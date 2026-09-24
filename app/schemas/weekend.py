from datetime import datetime, timedelta
from typing import Self

from pydantic import BaseModel

from app.schemas.country import Country


class Weekend(BaseModel):
    """A meeting's dates, country, circuit, UTC offset and cancellation flag."""

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
        """
        Convert an OpenF1 meeting and attach supplied country metadata.

        :param data: Meeting record including ``is_cancelled`` and ``gmt_offset``.
        :param country: Enriched country metadata, or None if supplied by the caller.
        :return: Weekend with parsed datetimes and a timedelta UTC offset.
        :raises KeyError: If a required field is missing.
        :raises pydantic.ValidationError: If the model fields fail validation.
        """
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
