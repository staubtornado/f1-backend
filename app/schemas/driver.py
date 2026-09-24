from typing import Self

from pydantic import BaseModel


class Driver(BaseModel):
    """Driver identity, team and base64-encoded portrait."""

    driver_id: int
    full_name: str
    first_name: str
    last_name: str
    acronym: str
    team_name: str
    portrait_base64: str

    @classmethod
    def from_openf1(cls, data: dict) -> Self:
        """
        Convert an enriched OpenF1 driver record.

        :param data: Driver record containing the added ``portrait_base64`` field.
        :return: Driver profile using the racing number as its identifier.
        :raises KeyError: If a required field is missing.
        :raises pydantic.ValidationError: If the model fields fail validation.
        """
        return cls(
            driver_id=data["driver_number"],
            full_name=data["full_name"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            acronym=data["name_acronym"],
            team_name=data["team_name"],
            portrait_base64=data["portrait_base64"],
        )
