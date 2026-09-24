from pydantic import BaseModel

from app.schemas.team_standing import TeamStanding


class TeamStandings(BaseModel):
    """Team championship standings for a season; the list may be empty."""

    season: int
    standings: list[TeamStanding]
