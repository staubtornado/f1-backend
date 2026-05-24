from enum import Enum


class DriverRaceEndStatus(str, Enum):
    FINISHED = "finished"
    DSQ = "dsq"
    DNF = "dnf"
    DNS = "dns"
