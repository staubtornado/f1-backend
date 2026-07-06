from typing import Self

from pydantic import BaseModel

from app.schemas.driver_race_end_status import DriverRaceEndStatus


class Classification(BaseModel):
    position: int
    driver_id: int
    status: DriverRaceEndStatus
    time: float | None
    laps_completed: int
    gap_to_leader: float | None
    gap_to_front: float | None

    @classmethod
    def from_openf1(cls, data: dict, gap_to_front: float | None) -> Self:
        status: DriverRaceEndStatus = DriverRaceEndStatus.FINISHED

        if data.get("dnf", False):
            status = DriverRaceEndStatus.DNF
        elif data.get("dsq", False):
            status = DriverRaceEndStatus.DSQ
        elif data.get("dns", False):
            status = DriverRaceEndStatus.DNS

        return cls(
            position=data["position"],
            driver_id=data["driver_number"],
            status=status,
            time=data.get("duration"),
            laps_completed=data["number_of_laps"],
            gap_to_leader=data.get("gap_to_leader"),
            gap_to_front=gap_to_front,
        )
