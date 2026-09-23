from datetime import datetime
from typing import Self

from pydantic import BaseModel

from app.schemas.driver import Driver


class RacePosition(BaseModel):
    driver: Driver
    timestamp: datetime
    position: int

    @classmethod
    def from_openf1(cls, data: dict, driver: Driver) -> Self:
        return cls(
            driver=driver,
            timestamp=data["date"],
            position=data["position"],
        )
