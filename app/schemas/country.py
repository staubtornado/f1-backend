from typing import Self

from pydantic import BaseModel


class Country(BaseModel):
    """Country metadata supplied by OpenF1, including an encoded flag."""

    id: int
    name: str
    alpha3_code: str
    flag_base64: str

    @classmethod
    def from_openf1(cls, data: dict) -> Self:
        """
        Create country metadata from an enriched meeting record.

        :param data: Meeting record whose ``country_flag`` already contains base64
            image data and whose ``country_key`` is an OpenF1 identifier.
        :return: Country model; the country key is not an ISO numeric code.
        :raises KeyError: If a required upstream field is missing.
        :raises ValueError: If the country key cannot be converted to an integer.
        :raises pydantic.ValidationError: If the model fields fail validation.
        """
        return cls(
            id=int(data["country_key"]),
            name=data["country_name"],
            alpha3_code=data["country_code"],
            flag_base64=data["country_flag"],
        )
