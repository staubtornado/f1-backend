from datetime import datetime
from typing import Self

from pydantic import BaseModel

from app.schemas.driver import Driver


class RacePosition(BaseModel):
    """A timestamped position update with the session's driver profile."""

    driver: Driver
    timestamp: datetime
    position: int

    @classmethod
    def from_openf1(cls, data: dict, driver: Driver) -> Self:
        """
        Combine an OpenF1 position update with a driver profile.

        :param data: Position record containing ``date`` and ``position``.
        :param driver: Profile selected by the caller for this record's driver.
        :return: Position update with its parsed timestamp. Driver identity is
            not cross-checked against the record.
        :raises KeyError: If a required field is missing.
        :raises pydantic.ValidationError: If the model fields fail validation.
        """
        return cls(
            driver=driver,
            timestamp=data["date"],
            position=data["position"],
        )
