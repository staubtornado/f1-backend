from pydantic import BaseModel

from app.schemas.circuit_type import CircuitType


class Circuit(BaseModel):
    """Circuit identity, image and circuit type."""

    id: int
    image_base64: str
    name: str
    circuit_type: CircuitType
