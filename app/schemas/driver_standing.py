from time import clock_settime
from typing import Self

from pydantic import BaseModel

class DriverStanding(BaseModel):
    position: int
    driver_id: int
    points: int

    @classmethod
    def from_openf1(cls, data: dict) -> Self:
        return cls(
            position=data["position_current"],
            driver_id=data["driver_number"],
            points=data["points_current"],
        )
        