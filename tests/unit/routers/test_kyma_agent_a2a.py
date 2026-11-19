"""Unit tests for the Kyma A2A agent router.

Covers:
- _build_human_content() helper
- KymaAgentExecutor.execute() happy path and error paths
- KymaAgentExecutor.cancel()
- build_kyma_a2a_app() factory
"""

import json
import time
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import fakeredis
import pytest
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueueLegacy
from a2a.types.a2a_pb2 import Message, Part, Role
from a2a.utils.errors import InternalError, InvalidParamsError, UnsupportedOperationError
from fastapi import HTTPException
from google.protobuf import json_format
from starlette.applications import Starlette
from starlette.testclient import TestClient

from agents.common.constants import ERROR_RATE_LIMIT_CODE
from agents.kyma.react_agent import UINavigationContext
from main import app
from routers.kyma_agent_a2a import (
    HTTP_EXCEPTION_STATE_KEY,
    KymaAgentExecutor,
    _build_human_content,
    build_kyma_a2a_app,
    check_token_usage,
    enforce_query_token_limit,
    get_cluster_id,
)
from services.usage import UsageExceedReport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request_context(
    text: str = "list all namespaces",
    metadata: dict | None = None,
) -> RequestContext:
    """Build a minimal mock RequestContext."""
    message = Message(
        role=Role.ROLE_USER,
        parts=[Part(text=text)],
        message_id="msg-1",
        context_id="ctx-1",
        task_id="task-1",
    )
    ctx = MagicMock(spec=RequestContext)
    ctx.message = message
    ctx.get_user_input.return_value = text
    ctx.metadata = metadata or {}
    ctx.call_context.state = {}
    return ctx


# ---------------------------------------------------------------------------
# _build_human_content
# ---------------------------------------------------------------------------


class TestBuildHumanContent:
    """Tests for _build_human_content helper."""

    def test_prepends_context_when_resource_kind_set(self):
        """UI context with resource_kind should be prepended to query."""
        query = "why is it failing?"
        ui_context = UINavigationContext(
            resource_kind="Function",
            resource_name="my-fn",
            resource_api_version="serverless.kyma-project.io/v1alpha2",
            namespace="default",
        )
        result = _build_human_content(query, ui_context)
        assert "Resource kind: Function" in result
        assert query in result
        assert result.index("Resource kind") < result.index(query)

    def test_returns_bare_query_when_context_empty(self):
        """Empty UI context (no resource kind) should not prepend anything."""
        query = "list all namespaces"
        ui_context = UINavigationContext(resource_kind="")
        result = _build_human_content(query, ui_context)
        assert result == query


# ---------------------------------------------------------------------------
# KymaAgentExecutor.execute
# ---------------------------------------------------------------------------


class TestKymaAgentExecutorExecute:
    """Tests for KymaAgentExecutor.execute()."""

    @pytest.fixture()
    def executor(self):
        """Return a bare KymaAgentExecutor instance."""
        return KymaAgentExecutor()

    @pytest.fixture(autouse=True)
    def usage_limit_not_exceeded(self):
        """Skip the token usage check, which is covered by TestUsageLimits."""
        with (
            patch("routers.kyma_agent_a2a.check_token_usage", new_callable=AsyncMock),
            patch("routers.kyma_agent_a2a.get_cluster_id", return_value="cluster"),
        ):
            yield

    @pytest.fixture()
    def event_queue(self):
        """Return an in-memory event queue."""
        return EventQueueLegacy()

    @pytest.mark.asyncio
    async def test_raises_invalid_params_when_message_is_none(self, executor, event_queue):
        """Execute should raise InvalidParamsError when message is None."""
        ctx = MagicMock(spec=RequestContext)
        ctx.message = None
        ctx.get_user_input.return_value = ""
        ctx.metadata = {}

        with pytest.raises(InvalidParamsError):
            await executor.execute(ctx, event_queue)

    @pytest.mark.asyncio
    async def test_raises_invalid_params_when_query_empty(self, executor, event_queue):
        """Execute should raise InvalidParamsError when query text is empty."""
        ctx = _make_request_context(text="")
        ctx.get_user_input.return_value = ""

        with pytest.raises(InvalidParamsError):
            await executor.execute(ctx, event_queue)

    @pytest.mark.asyncio
    async def test_happy_path_enqueues_message(self, executor, event_queue):
        """Execute should enqueue a Message with the agent's answer."""
        ctx = _make_request_context(
            text="list all namespaces",
            metadata={
                "x-session-id": "sess-123",
                "x-encrypted-key": "key",
                "x-client-iv": "iv",
                "x-target-cluster-encrypted": "enc",
                "namespace": "default",
                "resourceType": "Namespace",
                "resourceName": "",
                "groupVersion": "v1",
            },
        )
        expected_answer = "Here are the namespaces: default, kube-system"

        with (
            patch("routers.kyma_agent_a2a.init_config") as mock_config,
            patch("routers.kyma_agent_a2a.Redis") as mock_redis_cls,
            patch("routers.kyma_agent_a2a.EncryptionCache") as mock_enc_cls,
            patch(
                "routers.kyma_agent_a2a.get_k8s_auth_headers_from_encrypted_payload", new_callable=AsyncMock
            ) as mock_headers,
            patch("routers.kyma_agent_a2a.DataSanitizer") as mock_sanitizer_cls,
            patch("routers.kyma_agent_a2a.K8sClient") as mock_k8s_cls,
            patch("routers.kyma_agent_a2a._ModelsRegistry") as mock_models_cls,
            patch("routers.kyma_agent_a2a._SearchToolRegistry") as mock_search_registry_cls,
            patch("routers.kyma_agent_a2a.KymaReActAgent") as mock_agent_cls,
            patch("routers.kyma_agent_a2a.load_conversation_history", new_callable=AsyncMock) as mock_load,
            patch("routers.kyma_agent_a2a.save_conversation_history", new_callable=AsyncMock),
        ):
            mock_config.return_value = MagicMock(sanitization_config=None)
            mock_redis_cls.return_value = MagicMock()
            mock_enc_cls.return_value = MagicMock()
            mock_headers.return_value = MagicMock()
            mock_sanitizer_cls.return_value = MagicMock()
            mock_k8s_cls.return_value = MagicMock()
            mock_models_cls.return_value = MagicMock(models={})
            mock_search_registry_cls.return_value = MagicMock(tool=MagicMock())
            mock_load.return_value = []

            mock_agent_instance = AsyncMock()
            mock_agent_instance.ainvoke = AsyncMock(return_value=expected_answer)
            mock_agent_cls.return_value = mock_agent_instance

            await executor.execute(ctx, event_queue)

        event = await event_queue.dequeue_event()
        assert isinstance(event, Message)
        assert event.role == Role.ROLE_AGENT
        assert len(event.parts) == 1
        assert event.parts[0].text == expected_answer

        # The response must carry per-request metrics in its metadata, stored
        # natively as a nested object (no JSON-string double-encoding).
        metadata = json_format.MessageToDict(event.metadata)
        assert "x-metrics" in metadata
        metrics = metadata["x-metrics"]
        assert isinstance(metrics, dict)
        # Struct stores numbers as doubles, so integer counts round-trip as floats.
        assert {k: (int(v) if isinstance(v, float) else v) for k, v in metrics.items()} == {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "llm_call_count": 0,
            "tool_calls": [],
            "tool_call_count": 0,
            "tool_call_counts": {},
        }

    @pytest.mark.asyncio
    async def test_raises_internal_error_on_k8s_client_error(self, executor, event_queue):
        """Execute should raise InternalError when a K8sClientError occurs."""
        from utils.exceptions import K8sClientError

        ctx = _make_request_context(
            text="list pods",
            metadata={
                "x-session-id": "sess-1",
                "x-encrypted-key": "k",
                "x-client-iv": "iv",
                "x-target-cluster-encrypted": "enc",
            },
        )

        with (
            patch("routers.kyma_agent_a2a.init_config") as mock_config,
            patch("routers.kyma_agent_a2a.Redis"),
            patch("routers.kyma_agent_a2a.EncryptionCache"),
            patch(
                "routers.kyma_agent_a2a.get_k8s_auth_headers_from_encrypted_payload", new_callable=AsyncMock
            ) as mock_headers,
        ):
            mock_config.return_value = MagicMock(sanitization_config=None)
            mock_headers.side_effect = K8sClientError(
                message="cluster unreachable",
                status_code=503,
                uri="/api/v1/namespaces",
            )

            with pytest.raises(InternalError):
                await executor.execute(ctx, event_queue)

    @pytest.mark.asyncio
    async def test_raises_internal_error_on_unexpected_exception(self, executor, event_queue):
        """Execute should raise InternalError on any unexpected exception."""
        ctx = _make_request_context(text="list pods", metadata={"x-session-id": "sess-2"})

        with (
            patch("routers.kyma_agent_a2a.init_config", side_effect=RuntimeError("unexpected")),
            pytest.raises(InternalError),
        ):
            await executor.execute(ctx, event_queue)

    @pytest.mark.asyncio
    async def test_context_id_echoed_in_response(self, executor, event_queue):
        """Execute should echo the incoming context_id back in the response message."""
        ctx = _make_request_context(
            text="list pods",
            metadata={
                "x-session-id": "sess-123",
                "x-encrypted-key": "k",
                "x-client-iv": "iv",
                "x-target-cluster-encrypted": "enc",
            },
        )
        # ctx.message.context_id == "ctx-1" (set by _make_request_context)

        with (
            patch("routers.kyma_agent_a2a.init_config") as mock_config,
            patch("routers.kyma_agent_a2a.Redis"),
            patch("routers.kyma_agent_a2a.EncryptionCache"),
            patch(
                "routers.kyma_agent_a2a.get_k8s_auth_headers_from_encrypted_payload", new_callable=AsyncMock
            ) as mock_headers,
            patch("routers.kyma_agent_a2a.DataSanitizer"),
            patch("routers.kyma_agent_a2a.K8sClient"),
            patch("routers.kyma_agent_a2a._ModelsRegistry") as mock_models_cls,
            patch("routers.kyma_agent_a2a._SearchToolRegistry") as mock_search_registry_cls,
            patch("routers.kyma_agent_a2a.KymaReActAgent") as mock_agent_cls,
            patch("routers.kyma_agent_a2a.load_conversation_history", new_callable=AsyncMock) as mock_load,
            patch("routers.kyma_agent_a2a.save_conversation_history", new_callable=AsyncMock),
        ):
            mock_config.return_value = MagicMock(sanitization_config=None)
            mock_headers.return_value = MagicMock()
            mock_models_cls.return_value = MagicMock(models={})
            mock_search_registry_cls.return_value = MagicMock(tool=MagicMock())
            mock_load.return_value = []
            mock_agent_instance = AsyncMock()
            mock_agent_instance.ainvoke = AsyncMock(return_value="answer")
            mock_agent_cls.return_value = mock_agent_instance

            await executor.execute(ctx, event_queue)

        event = await event_queue.dequeue_event()
        assert isinstance(event, Message)
        assert event.context_id == "ctx-1"

    @pytest.mark.asyncio
    async def test_new_context_id_generated_and_echoed_when_missing(self, executor, event_queue):
        """Execute should generate and echo a new context_id when none is provided."""
        message = Message(
            role=Role.ROLE_USER,
            parts=[Part(text="list pods")],
            message_id="msg-1",
            context_id="",  # no context_id
            task_id="task-1",
        )
        ctx = MagicMock(spec=RequestContext)
        ctx.message = message
        ctx.get_user_input.return_value = "list pods"
        ctx.metadata = {"x-encrypted-key": "k", "x-client-iv": "iv", "x-target-cluster-encrypted": "enc"}

        with (
            patch("routers.kyma_agent_a2a.init_config") as mock_config,
            patch("routers.kyma_agent_a2a.Redis"),
            patch("routers.kyma_agent_a2a.EncryptionCache"),
            patch(
                "routers.kyma_agent_a2a.get_k8s_auth_headers_from_encrypted_payload", new_callable=AsyncMock
            ) as mock_headers,
            patch("routers.kyma_agent_a2a.DataSanitizer"),
            patch("routers.kyma_agent_a2a.K8sClient"),
            patch("routers.kyma_agent_a2a._ModelsRegistry") as mock_models_cls,
            patch("routers.kyma_agent_a2a._SearchToolRegistry") as mock_search_registry_cls,
            patch("routers.kyma_agent_a2a.KymaReActAgent") as mock_agent_cls,
            patch("routers.kyma_agent_a2a.load_conversation_history", new_callable=AsyncMock) as mock_load,
            patch("routers.kyma_agent_a2a.save_conversation_history", new_callable=AsyncMock),
            patch("routers.kyma_agent_a2a.create_session_id", return_value="generated-uuid") as mock_create_sid,
        ):
            mock_config.return_value = MagicMock(sanitization_config=None)
            mock_headers.return_value = MagicMock()
            mock_models_cls.return_value = MagicMock(models={})
            mock_search_registry_cls.return_value = MagicMock(tool=MagicMock())
            mock_load.return_value = []
            mock_agent_instance = AsyncMock()
            mock_agent_instance.ainvoke = AsyncMock(return_value="answer")
            mock_agent_cls.return_value = mock_agent_instance

            await executor.execute(ctx, event_queue)

            mock_create_sid.assert_called_once()

        event = await event_queue.dequeue_event()
        assert isinstance(event, Message)
        assert event.context_id == "generated-uuid"


# ---------------------------------------------------------------------------
# Token usage and query size limits
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# KymaAgentExecutor.cancel
# ---------------------------------------------------------------------------


class TestKymaAgentExecutorCancel:
    """Tests for KymaAgentExecutor.cancel()."""

    @pytest.mark.asyncio
    async def test_cancel_raises_unsupported_operation_error(self):
        """Cancel should raise UnsupportedOperationError since it is not supported."""
        executor = KymaAgentExecutor()
        ctx = MagicMock(spec=RequestContext)
        queue = EventQueueLegacy()

        with pytest.raises(UnsupportedOperationError):
            await executor.cancel(ctx, queue)


# ---------------------------------------------------------------------------
# build_kyma_a2a_app
# ---------------------------------------------------------------------------


class TestBuildKymaA2aApp:
    """Tests for build_kyma_a2a_app() factory."""

    def test_returns_starlette_application(self):
        """Factory should return a Starlette instance."""
        app = build_kyma_a2a_app()
        assert isinstance(app, Starlette)

    def test_has_agent_card_route(self):
        """The sub-app should expose the agent card well-known path."""
        app = build_kyma_a2a_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/.well-known/agent-card.json")
        assert response.status_code == 200  # noqa: PLR2004
        data = response.json()
        assert data["name"] == "Kyma Companion Agent"
        assert "skills" in data

    def test_chat_route_exists(self):
        """The sub-app should have a POST /chat route."""
        app = build_kyma_a2a_app()
        routes = {r.path for r in app.routes}  # type: ignore[attr-defined]
        assert "/chat" in routes

    def test_agent_card_contains_expected_fields(self):
        """Agent card should contain name, version, capabilities."""
        app = build_kyma_a2a_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/.well-known/agent-card.json")
        data = response.json()
        assert data.get("version") == "1.0.0"
        assert "capabilities" in data
