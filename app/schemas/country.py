from typing import Self

from pydantic import BaseModel


class Country(BaseModel):
    id: int
    name: str
    name_de: str
    alpha3_code: str
    subregion: str
    region: str
    flag_base64: str

    @classmethod
    def from_api_countries(cls, data: dict, flag_base64: str) -> Self:
        return cls(
            id=int(data["numericCode"]),
            name=data["name"],
            name_de=data["translations"]["de"],
            alpha3_code=data["alpha3Code"],
            subregion=data["subregion"],
            region=data["region"],
            flag_base64=flag_base64,
        )
