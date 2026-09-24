from enum import Enum


class DriverRaceEndStatus(str, Enum):
    """Normalized finish, disqualification, non-finish and non-start statuses."""

    FINISHED = "finished"
    DSQ = "dsq"
    DNF = "dnf"
    DNS = "dns"
