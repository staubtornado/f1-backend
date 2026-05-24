from pydantic import BaseModel

from app.schemas.driver_race_end_status import DriverRaceEndStatus


class Classification(BaseModel):
    position: int
    driver_id: int
    status: DriverRaceEndStatus
    time: str | None
    laps_completed: int
    gap_to_leader: int | None
    gap_to_person_in_front: int | None
