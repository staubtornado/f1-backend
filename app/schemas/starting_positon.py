from pydantic import BaseModel


class StartingPosition(BaseModel):
    """A grid position and the driver's racing number."""

    position: int
    driver_id: int
