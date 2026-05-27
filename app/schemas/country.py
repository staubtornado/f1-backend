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
    def from_rest_countries(cls, data: dict, flag_base64: str) -> Self:
        return cls(
            id=int(data["ccn3"]),
            name=data["name"]["common"],
            name_de=data["translations"]["deu"].get("common", ""),
            alpha3_code=data["cca3"],
            subregion=data["subregion"],
            region=data["region"],
            flag_base64=flag_base64,
        )
