from typing import Self

from pydantic import BaseModel


class TeamStanding(BaseModel):
    position: int
    team_name: str
    points: int

    @classmethod
    def from_openf1(cls, data: dict) -> Self:
        return cls(
            position=data["position_current"],
            team_name=data["team_name"],
            points=data["points_current"]
        )
