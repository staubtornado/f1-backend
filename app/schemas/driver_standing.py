from typing import Self

from pydantic import BaseModel


class DriverStanding(BaseModel):
    """A driver's current championship position and integer points."""

    position: int
    driver_id: int
    points: int

    @classmethod
    def from_openf1(cls, data: dict) -> Self:
        """
        Convert an OpenF1 driver championship record.

        :param data: Record containing ``position_current``, ``driver_number``
            and ``points_current``.
        :return: Driver standing with the current position and points.
        :raises KeyError: If a required field is missing.
        :raises pydantic.ValidationError: If values fail validation, including
            fractional points that cannot be represented by the integer model field.
        """
        return cls(
            position=data["position_current"],
            driver_id=data["driver_number"],
            points=data["points_current"],
        )
