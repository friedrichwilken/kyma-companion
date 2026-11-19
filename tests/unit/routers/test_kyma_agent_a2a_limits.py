"""Unit tests for the token usage and query size limits of the Kyma A2A endpoint."""

import json
import time
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import fakeredis
import pytest
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueueLegacy
from a2a.types.a2a_pb2 import Message, Part, Role
from a2a.utils.errors import InternalError
from fastapi import HTTPException
from starlette.testclient import TestClient

from agents.common.constants import ERROR_RATE_LIMIT_CODE
from main import app
from routers.a2a_http_status import HTTP_EXCEPTION_STATE_KEY
from routers.kyma_agent_a2a import KymaAgentExecutor, check_token_usage, enforce_query_token_limit, get_cluster_id
from services.usage import UsageExceedReport


def _make_request_context(text: str = "list all namespaces", metadata: dict | None = None) -> RequestContext:
    """Build a minimal mock RequestContext."""
    ctx = MagicMock(spec=RequestContext)
    ctx.message = Message(role=Role.ROLE_USER, parts=[Part(text=text)], message_id="msg-1", context_id="ctx-1")
    ctx.get_user_input.return_value = text
    ctx.metadata = metadata or {}
    ctx.call_context.state = {}
    return ctx


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "usage_report, expected_exception",
    [
        (None, None),
        (
            UsageExceedReport(cluster_id="k8s-id", token_limit=1000, total_tokens_used=1000, reset_seconds_left=60),
            HTTPException,
        ),
    ],
)
async def test_check_token_usage(usage_report, expected_exception):
    mock_usage_tracker = Mock()
    mock_usage_tracker.ais_usage_limit_exceeded = AsyncMock(return_value=usage_report)

    if expected_exception:
        with pytest.raises(expected_exception) as exc_info:
            await check_token_usage("k8s-id", mock_usage_tracker)
        assert exc_info.value.status_code == ERROR_RATE_LIMIT_CODE
        assert exc_info.value.detail == {
            "error": "Token usage limit exceeded",
            "message": "Token usage limit of 1000 exceeded for this cluster. "
            "To ensure a fair usage, Joule controls the number of requests a cluster can make within 24 hours.",
            "current_usage": 1000,
            "limit": 1000,
            "time_remaining_seconds": 60,
        }
        assert exc_info.value.headers == {"Retry-After": "60"}
    else:
        await check_token_usage("k8s-id", mock_usage_tracker)
    mock_usage_tracker.ais_usage_limit_exceeded.assert_called_once_with("k8s-id")


@pytest.mark.parametrize(
    "mock_token_count, should_raise_exception",
    [
        (500, False),  # Within limit
        (8000, False),  # At limit
        (9000, True),  # Exceeds limit
    ],
)
def test_enforce_query_token_limit(mock_token_count, should_raise_exception):
    with patch("routers.kyma_agent_a2a.compute_string_token_count") as mock_token_counter:
        mock_token_counter.return_value = mock_token_count

        if should_raise_exception:
            with pytest.raises(HTTPException) as exc_info:
                enforce_query_token_limit("What is Kubernetes?")

            assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
            assert exc_info.value.detail == "Input Query exceeds the allowed token limit."
        else:
            enforce_query_token_limit("What is Kubernetes?")  # Should not raise


@pytest.mark.parametrize(
    "cluster_url, expected_cluster_id",
    [
        ("https://api.c-123.kyma.example.com", "c-123"),
        ("https://api.c-123.kyma.example.com:443/", "c-123"),
        ("https://API.C-123.kyma.example.com", "c-123"),
    ],
)
def test_get_cluster_id(cluster_url, expected_cluster_id):
    assert get_cluster_id(cluster_url) == expected_cluster_id


@pytest.mark.parametrize(
    "cluster_url",
    [
        "https://localhost",
        "https://api.*.example.com",
        "https://api.c[1].example.com",
        "https://api.c_1.example.com",
        "https://api.-c1.example.com",
        "https://api..example.com",
        f"https://api.{'c' * 64}.example.com",
        "not a url",
        "https://[::1",
    ],
)
def test_get_cluster_id_rejects_invalid_id(cluster_url):
    with pytest.raises(HTTPException) as exc_info:
        get_cluster_id(cluster_url)

    assert exc_info.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


_SEND_MESSAGE_REQUESTS = [
    (
        "message/send",
        {"role": "user", "parts": [{"kind": "text", "text": "list pods"}], "messageId": "m", "contextId": "c"},
        {},
    ),
    (
        "SendMessage",
        {"role": "ROLE_USER", "parts": [{"text": "list pods"}], "messageId": "m", "contextId": "c"},
        {"A2A-Version": "1.0"},
    ),
]


class TestUsageLimits:
    """Tests for the token usage and query size limits of KymaAgentExecutor.execute()."""

    @pytest.fixture()
    def mocks(self):
        """Patch the executor dependencies, keeping the limit checks and a fake Redis."""
        redis = MagicMock()
        redis.has_connection.return_value = True
        server = fakeredis.FakeServer()
        redis.get_connection.return_value = fakeredis.FakeAsyncRedis(server=server)
        with (
            patch("routers.kyma_agent_a2a.init_config") as mock_config,
            patch("routers.kyma_agent_a2a.Redis", return_value=redis),
            patch("routers.kyma_agent_a2a.EncryptionCache"),
            patch("routers.kyma_agent_a2a.get_k8s_auth_headers_from_encrypted_payload", new_callable=AsyncMock),
            patch("routers.kyma_agent_a2a.DataSanitizer"),
            patch("routers.kyma_agent_a2a.K8sClient") as mock_k8s_client_cls,
            patch("routers.kyma_agent_a2a._ModelsRegistry") as mock_models_cls,
            patch("routers.kyma_agent_a2a._SearchToolRegistry") as mock_search_registry_cls,
            patch("routers.kyma_agent_a2a.KymaReActAgent") as mock_agent_cls,
            patch("routers.kyma_agent_a2a.load_conversation_history", new_callable=AsyncMock) as mock_load,
            patch("routers.kyma_agent_a2a.save_conversation_history", new_callable=AsyncMock),
            patch("routers.kyma_agent_a2a.UsageTrackerCallback"),
        ):
            mock_config.return_value = MagicMock(sanitization_config=None)
            mock_k8s_client_cls.return_value.get_api_server.return_value = "https://api.k8s-id.example.com"
            mock_models_cls.return_value = MagicMock(models={})
            mock_search_registry_cls.return_value = MagicMock(tool=MagicMock())
            mock_load.return_value = []
            mock_agent_cls.return_value.ainvoke = AsyncMock(return_value="answer")
            yield MagicMock(
                agent=mock_agent_cls.return_value,
                k8s_client=mock_k8s_client_cls.return_value,
                redis=fakeredis.FakeRedis(server=server),
            )

    @staticmethod
    def _write_usage(redis: fakeredis.FakeRedis, cluster_id: str, total: int) -> None:
        epoch = time.time() - 10
        usage = {"input": total, "output": 0, "total": total, "epoch": epoch}
        key = f"llm_usage_{cluster_id}_{epoch}"
        redis.set(key, json.dumps(usage))
        redis.zadd(f"llm_usage:index:{cluster_id}", {key: epoch})

    @pytest.mark.asyncio
    async def test_under_limit_passes(self, mocks):
        self._write_usage(mocks.redis, "k8s-id", 999)
        event_queue = EventQueueLegacy()

        with patch("routers.kyma_agent_a2a.TOKEN_LIMIT_PER_CLUSTER", 1000):
            await KymaAgentExecutor().execute(_make_request_context(), event_queue)

        assert isinstance(await event_queue.dequeue_event(), Message)

    @pytest.mark.asyncio
    async def test_usage_of_other_cluster_is_not_counted(self, mocks):
        self._write_usage(mocks.redis, "other-id", 5000)
        event_queue = EventQueueLegacy()

        with patch("routers.kyma_agent_a2a.TOKEN_LIMIT_PER_CLUSTER", 1000):
            await KymaAgentExecutor().execute(_make_request_context(), event_queue)

        assert isinstance(await event_queue.dequeue_event(), Message)

    @pytest.mark.asyncio
    async def test_over_limit_is_rejected_before_agent_is_invoked(self, mocks):
        self._write_usage(mocks.redis, "k8s-id", 1000)
        ctx = _make_request_context()

        with (
            patch("routers.kyma_agent_a2a.TOKEN_LIMIT_PER_CLUSTER", 1000),
            pytest.raises(HTTPException) as exc_info,
        ):
            await KymaAgentExecutor().execute(ctx, EventQueueLegacy())

        assert exc_info.value.status_code == ERROR_RATE_LIMIT_CODE
        assert ctx.call_context.state[HTTP_EXCEPTION_STATE_KEY] is exc_info.value
        mocks.agent.ainvoke.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_disabled_limit_passes(self, mocks):
        self._write_usage(mocks.redis, "k8s-id", 10**9)
        event_queue = EventQueueLegacy()

        with patch("routers.kyma_agent_a2a.TOKEN_LIMIT_PER_CLUSTER", -1):
            await KymaAgentExecutor().execute(_make_request_context(), event_queue)

        assert isinstance(await event_queue.dequeue_event(), Message)

    @pytest.mark.asyncio
    async def test_oversized_query_is_rejected_before_agent_is_invoked(self, mocks):
        ctx = _make_request_context(text="list pods " * 20)

        with (
            patch("routers.kyma_agent_a2a.MAX_TOKEN_LIMIT_INPUT_QUERY", 10),
            pytest.raises(HTTPException) as exc_info,
        ):
            await KymaAgentExecutor().execute(ctx, EventQueueLegacy())

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        assert ctx.call_context.state[HTTP_EXCEPTION_STATE_KEY] is exc_info.value
        mocks.agent.ainvoke.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_oversized_ui_context_is_rejected_before_agent_is_invoked(self, mocks):
        # the UI context from the metadata is sent to the model together with the query.
        ctx = _make_request_context(text="why?", metadata={"resourceType": "Pod", "resourceName": "x" * 500})

        with (
            patch("routers.kyma_agent_a2a.MAX_TOKEN_LIMIT_INPUT_QUERY", 50),
            pytest.raises(HTTPException) as exc_info,
        ):
            await KymaAgentExecutor().execute(ctx, EventQueueLegacy())

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        mocks.agent.ainvoke.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cluster_id_is_case_insensitive(self, mocks):
        self._write_usage(mocks.redis, "k8s-id", 1000)
        mocks.k8s_client.get_api_server.return_value = "https://API.K8S-ID.example.com"

        with (
            patch("routers.kyma_agent_a2a.TOKEN_LIMIT_PER_CLUSTER", 1000),
            pytest.raises(HTTPException) as exc_info,
        ):
            await KymaAgentExecutor().execute(_make_request_context(), EventQueueLegacy())

        assert exc_info.value.status_code == ERROR_RATE_LIMIT_CODE

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "cluster_url", ["https://api.*.example.com", "https://api.k8s-id_x.example.com", "https://localhost"]
    )
    async def test_invalid_cluster_id_is_rejected_before_agent_is_invoked(self, mocks, cluster_url):
        mocks.k8s_client.get_api_server.return_value = cluster_url

        with pytest.raises(InternalError):
            await KymaAgentExecutor().execute(_make_request_context(), EventQueueLegacy())

        mocks.agent.ainvoke.assert_not_awaited()

    @pytest.mark.parametrize("method, message, headers", _SEND_MESSAGE_REQUESTS)
    def test_chat_endpoint_returns_429_when_over_limit(self, mocks, method, message, headers):
        client = TestClient(app)
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": {"message": message}}
        self._write_usage(mocks.redis, "k8s-id", 1500)

        with patch("routers.kyma_agent_a2a.TOKEN_LIMIT_PER_CLUSTER", 1000):
            response = client.post("/api/agent/kyma/chat", json=body, headers=headers)

        assert response.status_code == ERROR_RATE_LIMIT_CODE
        response_body = response.json()
        time_remaining = response_body.pop("time_remaining_seconds")
        assert response_body == {
            "error": "Token usage limit exceeded",
            "message": "Token usage limit of 1000 exceeded for this cluster. "
            "To ensure a fair usage, Joule controls the number of requests a cluster can make within 24 hours.",
            "current_usage": 1500,
            "limit": 1000,
        }
        assert 0 < time_remaining <= 86400  # noqa: PLR2004
        assert response.headers["Retry-After"] == str(time_remaining)
        mocks.agent.ainvoke.assert_not_awaited()

    @pytest.mark.parametrize("method, message, headers", _SEND_MESSAGE_REQUESTS)
    def test_chat_endpoint_returns_400_for_oversized_query(self, mocks, method, message, headers):
        client = TestClient(app)
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": {"message": message}}

        with patch("routers.kyma_agent_a2a.MAX_TOKEN_LIMIT_INPUT_QUERY", 1):
            response = client.post("/api/agent/kyma/chat", json=body, headers=headers)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json() == {"error": "Bad Request", "message": "Invalid request format or parameters"}
        mocks.agent.ainvoke.assert_not_awaited()
