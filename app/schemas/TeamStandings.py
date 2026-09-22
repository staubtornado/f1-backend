from pydantic import BaseModel

from app.schemas.team_standing import TeamStanding


class TeamStandings(BaseModel):
    season: int
    standings: list[TeamStanding]
