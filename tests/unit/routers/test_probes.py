from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE

from main import app
from routers.probes import ILLMProbe, IRedis, IUsageTrackerProbe
from services.probes import get_llm_probe, get_usage_tracker_probe
from services.redis import get_redis


@pytest.mark.parametrize(
    "test_case, redis_ready, usage_tracker_ready, llm_states, key_store_ready, expected_status",
    [
        ("all ready", True, True, {"model1": True, "model2": True}, True, HTTP_200_OK),
        (
            "Redis not ready",
            False,
            True,
            {"model1": True, "model2": True},
            True,
            HTTP_503_SERVICE_UNAVAILABLE,
        ),
        (
            "one model not ready",
            True,
            True,
            {"model1": False, "model2": True},
            True,
            HTTP_503_SERVICE_UNAVAILABLE,
        ),
        ("no models", True, True, {}, True, HTTP_503_SERVICE_UNAVAILABLE),
        (
            "usage_tracker not ready",
            True,
            False,
            {"model1": True, "model2": True},
            True,
            HTTP_503_SERVICE_UNAVAILABLE,
        ),
        (
            "key_store not ready",
            True,
            True,
            {"model1": True, "model2": True},
            False,
            HTTP_503_SERVICE_UNAVAILABLE,
        ),
    ],
)
def test_healthz_probe(
    test_case,
    redis_ready,
    usage_tracker_ready,
    llm_states,
    key_store_ready,
    expected_status,
):
    """
    Test the health probe endpoint. This test ensures that the endpoint returns the correct status code.
    """
    # Given:
    mock_redis = MagicMock(spec=IRedis)
    mock_redis.is_connection_operational = AsyncMock(return_value=redis_ready)
    app.dependency_overrides[get_redis] = lambda: mock_redis

    usage_tracker_probe = MagicMock(spec=IUsageTrackerProbe)
    usage_tracker_probe.is_healthy = MagicMock(return_value=usage_tracker_ready)
    app.dependency_overrides[get_usage_tracker_probe] = lambda: usage_tracker_probe

    mock_llm_probe = MagicMock(spec=ILLMProbe)
    mock_llm_probe.get_llms_states.return_value = llm_states
    app.dependency_overrides[get_llm_probe] = lambda: mock_llm_probe

    mock_key_store = MagicMock()
    mock_key_store.is_healthy.return_value = key_store_ready

    # When:
    with patch("routers.probes.KeyStore", return_value=mock_key_store):
        client = TestClient(app)
        response = client.get("/healthz")

    # Then:
    assert response.status_code == expected_status, test_case
    data = response.json()
    assert "is_redis_healthy" in data, test_case
    assert "is_usage_tracker_healthy" in data, test_case
    assert "is_key_store_healthy" in data, test_case
    assert "llms" in data, test_case
    assert data["is_key_store_healthy"] == key_store_ready, test_case

    # Clean up.
    app.dependency_overrides = {}


@pytest.mark.parametrize(
    "test_case, redis_ready, llm_states, key_store_ready, expected_status",
    [
        ("all ready", True, True, True, HTTP_200_OK),
        ("no Redis connection", False, True, True, HTTP_503_SERVICE_UNAVAILABLE),
        ("no models", True, False, True, HTTP_503_SERVICE_UNAVAILABLE),
        ("key_store not ready", True, True, False, HTTP_503_SERVICE_UNAVAILABLE),
    ],
)
def test_ready_probe(test_case, redis_ready, llm_states, key_store_ready, expected_status):
    """
    Test the readiness probe endpoint. This test ensures that the endpoint returns the correct status code.
    """
    # Given:
    mock_redis = MagicMock(spec=IRedis)
    mock_redis.has_connection.return_value = redis_ready
    app.dependency_overrides[get_redis] = lambda: mock_redis

    mock_llm_probe = MagicMock(spec=ILLMProbe)
    mock_llm_probe.has_models.return_value = llm_states
    app.dependency_overrides[get_llm_probe] = lambda: mock_llm_probe

    mock_key_store = MagicMock()
    mock_key_store.is_healthy.return_value = key_store_ready

    # When:
    with patch("routers.probes.KeyStore", return_value=mock_key_store):
        client = TestClient(app)
        response = client.get("/readyz")

    # Then:
    assert response.status_code == expected_status, test_case
    data = response.json()
    assert "is_redis_initialized" in data, test_case
    assert "are_models_initialized" in data, test_case
    assert "is_key_store_initialized" in data, test_case
    assert data["is_key_store_initialized"] == key_store_ready, test_case

    # Clean up.
    app.dependency_overrides = {}
