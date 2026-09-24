from pydantic import BaseModel

from app.schemas.driver_standing import DriverStanding


class DriverStandings(BaseModel):
    """Driver championship standings for a season; the list may be empty."""

    season: int
    standings: list[DriverStanding]
