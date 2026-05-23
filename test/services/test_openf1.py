import pytest
import json
from pathlib import Path
from app.services.openf1 import OpenF1
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
    """Testet die get_seasons Methode des OpenF1 Services, dass sie die Jahre sortiert zurückgibt"""
    data = json.loads(SESSIONS_SAMPLE)

    resp = MagicMock()
    resp.json = lambda: data
    resp.raise_for_status = lambda: None
    openf1_service._client.get.return_value = resp

    seasons = await openf1_service.get_seasons()

    assert seasons == [2019, 2020, 2021, 2022, 2023, 2024, 2026]