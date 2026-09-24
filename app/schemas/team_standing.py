from typing import Self

from pydantic import BaseModel


class TeamStanding(BaseModel):
    """A team's current championship position and integer points."""

    position: int
    team_name: str
    points: int

    @classmethod
    def from_openf1(cls, data: dict) -> Self:
        """
        Convert an OpenF1 team championship record.

        :param data: Record containing ``position_current``, ``team_name``
            and ``points_current``.
        :return: Team standing with the current position and points.
        :raises KeyError: If a required field is missing.
        :raises pydantic.ValidationError: If values fail validation, including
            fractional points that cannot be represented by the integer model field.
        """
        return cls(
            position=data["position_current"],
            team_name=data["team_name"],
            points=data["points_current"]
        )
