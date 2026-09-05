from pydantic import BaseModel


class Driver(BaseModel):
    driver_id: int
    full_name: str
    first_name: str
    last_name: str
    acronym: str
    team_name: str
    portrait_base64: str
