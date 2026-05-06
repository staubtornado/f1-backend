from enum import Enum


class CircuitType(str, Enum):
    STREET = "street"
    PERMANENT = "permanent"