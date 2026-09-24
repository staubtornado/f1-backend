from enum import Enum


class CircuitType(str, Enum):
    """Circuit categories; temporary road circuits serialize as ``temporary_track``."""

    TEMPORARY_STREET = "temporary_street"
    TEMPORARY_ROAD = "temporary_track"
    PERMANENT = "permanent"
