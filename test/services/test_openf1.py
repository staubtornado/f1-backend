import pytest
import json
from pathlib import Path
from app.services.openf1 import OpenF1
from app.schemas.weekend import Weekend
from app.schemas.session import Session
from app.schemas.session_type import *
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_async_client():
    """Erstellt einen gemockten AsyncClient für die Tests"""
    return AsyncMock()

@pytest.fixture
def openf1_service(mock_async_client):
    """Erstellt einen OpenF1 Service mit dem gemockten AsyncClient"""
    return OpenF1(client=mock_async_client)

SESSIONS_SAMPLE = Path("test/fixtures/sessions_sample.json").read_text()

@pytest.mark.asyncio
async def test_get_seasons(openf1_service):
    """Stellt sicher, dass get_seasons die Jahre der Saisons mit vorhandenen Daten sortiert zurückgibt"""
    data = json.loads(SESSIONS_SAMPLE)

    resp = MagicMock()
    resp.json = lambda: data
    resp.raise_for_status = lambda: None
    openf1_service._client.get.return_value = resp

    seasons = await openf1_service.get_seasons()

    assert seasons == [2019, 2020, 2021, 2022, 2023, 2024, 2026]

WEEKENDS_SAMPLE = Path("test/fixtures/weekends_sample.json").read_text()

@pytest.mark.asyncio
async def test_get_season_weekends_converts_data(openf1_service):
    """Stellt sicher, dass get_season_weekends die Wochenenden einer Saison in Weekend-Modelle umwandelt"""
    data = json.loads(WEEKENDS_SAMPLE)

    resp = MagicMock()
    resp.json = lambda: data
    resp.raise_for_status = lambda: None
    openf1_service._client.get.return_value = resp

    weekends = await openf1_service.get_season_weekends(2023)

    assert isinstance(weekends, list)
    assert len(weekends) == 2
    assert isinstance(weekends[0], Weekend)
    assert weekends[0].id == 1228
    assert weekends[0].name == "Pre-Season Testing"
    assert weekends[0].circuit_id == 63

WEEKEND_SESSIONS_SAMPLE = Path("test/fixtures/weekend_sessions_sample.json").read_text()

@pytest.mark.asyncio
async def test_get_weekend_sessions_converts_data(openf1_service):
    """Stellt sicher, dass get_weekend_sessions die Sessions eines Wochenendes in Session-Modelle umwandelt"""
    data = json.loads(WEEKEND_SESSIONS_SAMPLE)

    resp = MagicMock()
    resp.json = lambda: data
    resp.raise_for_status = lambda: None
    openf1_service._client.get.return_value = resp

    sessions = await openf1_service.get_weekend_sessions(1229)

    assert isinstance(sessions, list)
    assert len(sessions) == 5
    assert isinstance(sessions[0], Session)
    assert sessions[0].id == 9465
    assert sessions[0].type == SessionType.PRACTICE_ONE
    assert sessions[0].weekend_id == 1229