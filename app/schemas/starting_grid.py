from pydantic import BaseModel


class StartingGrid(BaseModel):
    position: int
    driver_id: int
    lap_duration: float | int
