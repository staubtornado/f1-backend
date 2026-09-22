from pydantic import BaseModel


class StartingPosition(BaseModel):
    position: int
    driver_id: int
