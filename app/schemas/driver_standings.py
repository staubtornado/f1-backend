from typing import Self

from pydantic import BaseModel

from app.schemas.driver_standing import DriverStanding

class DriverStandings(BaseModel):
    season: int
    standings: list[DriverStanding]

