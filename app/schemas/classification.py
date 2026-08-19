from typing import Self

from pydantic import BaseModel

from app.schemas.driver_race_end_status import DriverRaceEndStatus


class Classification(BaseModel):
    position: int
    driver_id: int
    status: DriverRaceEndStatus
    time: float | int | None
    laps_completed: int
    gap_to_leader: float | int | None
    gap_to_front: float | int | None

    @classmethod
    def from_openf1(cls, data: dict, front_classification: Self | None) -> Self:
        if data.get("position") is None:
            raise ValueError("Invalid classification data")

        status: DriverRaceEndStatus = DriverRaceEndStatus.FINISHED

        if data.get("dnf", False):
            status = DriverRaceEndStatus.DNF
        elif data.get("dsq", False):
            status = DriverRaceEndStatus.DSQ
        elif data.get("dns", False):
            status = DriverRaceEndStatus.DNS

        if isinstance(data.get("duration"), list):
            data["duration"] = list(
                filter(lambda t: t is not None, data["duration"])
            )[-1]

        if isinstance(data.get("gap_to_leader"), list):
            data["gap_to_leader"] = list(
                filter(lambda t: t is not None, data["gap_to_leader"])
            )[-1]

        gap_to_front = None
        if front_classification and front_classification.time:
            if isinstance(own_time := data.get("duration"), (int, float)):
                gap_to_front = own_time - front_classification.time

        return cls(
            position=data["position"],
            driver_id=data["driver_number"],
            status=status,
            time=data.get("duration"),
            laps_completed=data["number_of_laps"],
            gap_to_leader=data.get("gap_to_leader"),
            gap_to_front=gap_to_front,
        )
