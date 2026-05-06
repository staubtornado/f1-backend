from enum import Enum


class SessionType(str, Enum):
    QUALIFYING = "qualifying"
    PRACTICE_ONE = "practice_one"
    PRACTICE_TWO = "practice_two"
    PRACTICE_THREE = "practice_three"
    SPRINT = "sprint"
    SPRINT_QUALIFYING = "sprint_qualifying"
    GRAND_PRIX = "grand_prix"