from typing import Self

from pydantic import BaseModel


class Country(BaseModel):
    id: int
    name: str
    alpha3_code: str
    flag_base64: str

    @classmethod
    def from_openf1(cls, data: dict) -> Self:
        return cls(
            id=int(data["country_key"]),
            name=data["country_name"],
            alpha3_code=data["country_code"],
            flag_base64=data["country_flag"],
        )
