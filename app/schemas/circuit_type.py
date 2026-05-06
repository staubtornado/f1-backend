from enum import Enum


class CircuitType(str, Enum):
    TEMPORARY_STREET = "temporary_street"
    TEMPORARY_ROAD = "temporary_track"
    PERMANENT = "permanent"