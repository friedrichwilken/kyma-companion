"""A2A (Agent-to-Agent) executor and sub-app for the Kyma ReAct Agent.

Bridges A2A protocol `message/send` JSON-RPC requests to the existing
KymaReActAgent, extracting K8s authentication and resource context from
message metadata.

Exposed routes (relative to the mount point /api/agent/kyma):
  GET /.well-known/agent-card.json   – agent card discovery
  POST /chat                         – A2A JSON-RPC endpoint
"""

import re
from http import HTTPStatus
from typing import Any, cast
from urllib.parse import urlparse

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from a2a.types.a2a_pb2 import Message, Part, Role
from a2a.utils.errors import InternalError, InvalidParamsError, UnsupportedOperationError
from fastapi import HTTPException
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Struct
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage
from starlette.applications import Starlette
from starlette.routing import Route

from agents.common.constants import ERROR_RATE_LIMIT_CODE
from agents.common.utils import compute_string_token_count
from agents.kyma.react_agent import KymaReActAgent, UINavigationContext
from agents.memory.async_redis_checkpointer import AsyncRedisSaver, IUsageMemory
from routers.a2a_http_status import (
    create_jsonrpc_routes_with_http_status,
    is_recorded_http_exception,
    record_http_exception,
)
from routers.common import (
    _ModelsRegistry,
    _SearchToolRegistry,
    get_k8s_auth_headers_from_encrypted_payload,
    init_config,
    load_conversation_history,
    save_conversation_history,
)
from services.data_sanitizer import DataSanitizer
from services.encryption_cache import EncryptionCache
from services.k8s import K8sClient
from services.redis import Redis
from services.usage import RequestMetricsCallback, UsageTracker, UsageTrackerCallback
from utils.exceptions import K8sClientError
from utils.logging import get_logger
from utils.settings import (
    MAIN_MODEL_NAME,
    MAX_TOKEN_LIMIT_INPUT_QUERY,
    TOKEN_LIMIT_PER_CLUSTER,
    TOKEN_USAGE_RESET_INTERVAL,
)
from utils.utils import create_session_id

logger = get_logger(__name__)

# A cluster host name has at least two labels; the second one is the cluster ID.
MIN_CLUSTER_HOST_LABELS = 2
_CLUSTER_ID_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


def _build_human_content(query: str, ui_context: UINavigationContext) -> str:
    """Prepend the UI navigation context message to the user query if available.

    Args:
        query: The raw user query string.
        ui_context: The UI navigation context from message metadata.

    Returns:
        Combined context string, or the bare query when context is empty.
    """
    context_message = ui_context.as_context_message()
    if context_message.strip():
        return f"{context_message}\n\n{query}"
    return query


def get_cluster_id(cluster_url: str) -> str:
    """Return the ID of the cluster under which its token usage is recorded.

    The ID is the second label of the host name of the cluster URL, for example `c-123`
    for `https://api.c-123.kyma.example.com`. It must be a lower-case DNS label, because
    it is part of Redis keys: it cannot contain the key separator `_`, Redis pattern
    characters or upper-case variants of the same ID.
    """
    try:
        host = urlparse(cluster_url).hostname or ""
    except ValueError:
        host = ""
    labels = host.split(".")
    if len(labels) < MIN_CLUSTER_HOST_LABELS or _CLUSTER_ID_PATTERN.fullmatch(labels[1]) is None:
        raise HTTPException(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail="Invalid cluster URL.")
    return labels[1]


def enforce_query_token_limit(query: str) -> None:
    """Enforce query token limit to input request."""
    token_count = compute_string_token_count(query, MAIN_MODEL_NAME)
    logger.info(f"Input Query Token count is {token_count}")
    if token_count > MAX_TOKEN_LIMIT_INPUT_QUERY:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Input Query exceeds the allowed token limit.")


async def check_token_usage(cluster_id: str, usage_tracker: UsageTracker) -> None:
    """Check if the token usage limit is exceeded for the cluster."""
    report = await usage_tracker.ais_usage_limit_exceeded(cluster_id)
    if report is not None:
        raise HTTPException(
            status_code=ERROR_RATE_LIMIT_CODE,
            detail={
                "error": "Token usage limit exceeded",
                "message": f"Token usage limit of {report.token_limit} exceeded for this cluster. "
                f"To ensure a fair usage, Joule controls the number"
                f" of requests a cluster can make within 24 hours.",
                "current_usage": report.total_tokens_used,
                "limit": report.token_limit,
                "time_remaining_seconds": report.reset_seconds_left,
            },
            headers={"Retry-After": str(report.reset_seconds_left)},
        )


async def enforce_limits(
    context: RequestContext, human_content: str, cluster_id: str, usage_memory: IUsageMemory
) -> None:
    """Enforce the query size limit and the token usage limit of the cluster.

    `human_content` is the query together with the UI context, as sent to the model.
    A violation is recorded, so that the client receives its HTTP status.
    """
    try:
        enforce_query_token_limit(human_content)
        usage_tracker = UsageTracker(usage_memory, TOKEN_LIMIT_PER_CLUSTER, TOKEN_USAGE_RESET_INTERVAL)
        await check_token_usage(cluster_id, usage_tracker)
    except HTTPException as exc:
        record_http_exception(context, exc)
        raise


class KymaAgentExecutor(AgentExecutor):
    """A2A AgentExecutor that delegates to the Kyma ReAct Agent.

    Reads K8s cluster authentication and resource context from
    request metadata:
      - x-session-id                → ECDH session for encrypted key lookup
      - x-encrypted-key             → AES key ciphertext
      - x-client-iv                 → AES-GCM nonce
      - x-target-cluster-encrypted  → encrypted cluster auth payload
      - namespace                   → resource namespace (optional)
      - resourceType                → resource kind (optional, e.g. "ConfigMap")
      - resourceName                → resource name (optional)
      - groupVersion                → API version (optional, e.g. "v1")
    """

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute a Kyma agent request and push the result into event_queue.

        Args:
            context: The A2A request context with message and metadata.
            event_queue: Queue to publish the agent response Message to.
        """
        message = context.message
        if message is None:
            raise InvalidParamsError(message="Missing message in request")

        query = context.get_user_input()
        if not query:
            raise InvalidParamsError(message="Empty or missing text in message parts")

        # Use the A2A context_id as the session key for conversation history.
        # If absent, generate a new one and echo it back in the response so the
        # caller can continue the same conversation in subsequent requests.
        session_id = message.context_id or create_session_id()

        # metadata lives in params.message.metadata (protobuf Struct), not
        # params.metadata (request-level, always empty for message/send calls)
        metadata: dict[str, Any] = json_format.MessageToDict(message.metadata) if message.HasField("metadata") else {}
        # Merge with request-level metadata as fallback
        metadata = {**context.metadata, **metadata}

        try:
            config = init_config()
            redis_conn = Redis()
            encryption_cache = EncryptionCache(redis=redis_conn)
            k8s_auth_headers = await get_k8s_auth_headers_from_encrypted_payload(
                x_encrypted_key=str(metadata.get("x-encrypted-key", "")),
                x_client_iv=str(metadata.get("x-client-iv", "")),
                x_session_id=str(metadata.get("x-session-id", "")),
                x_target_cluster_encrypted=str(metadata.get("x-target-cluster-encrypted", "")),
                encryption_cache=encryption_cache,
            )
            data_sanitizer = DataSanitizer(config.sanitization_config)
            k8s_client = K8sClient(k8s_auth_headers=k8s_auth_headers, data_sanitizer=data_sanitizer)

            models = _ModelsRegistry(config).models
            agent = KymaReActAgent(models=models, k8s_client=k8s_client, search_tool=_SearchToolRegistry(models).tool)

            chat_history = await load_conversation_history(redis_conn, session_id)
            ui_context = UINavigationContext(
                resource_kind=str(metadata.get("resourceType", "")),
                resource_name=str(metadata.get("resourceName", "")),
                resource_api_version=str(metadata.get("groupVersion", "")),
                namespace=str(metadata.get("namespace", "")),
            )

            human_content = _build_human_content(query, ui_context)

            # Enforce the limits before the model is used.
            cluster_id = get_cluster_id(k8s_client.get_api_server())
            usage_memory = AsyncRedisSaver(redis_conn.get_connection())
            await enforce_limits(context, human_content, cluster_id, cast(IUsageMemory, usage_memory))

            request_metrics = RequestMetricsCallback()
            callbacks: list[BaseCallbackHandler] = [
                UsageTrackerCallback(cluster_id, cast(IUsageMemory, usage_memory)),
                request_metrics,
            ]

            answer = await agent.ainvoke(query, chat_history=chat_history, ui_context=ui_context, callbacks=callbacks)

            new_messages = [*chat_history, HumanMessage(content=human_content), AIMessage(content=answer)]
            await save_conversation_history(redis_conn, session_id, new_messages)

            # Attach per-request metrics (token usage, tool calls, LLM calls) to the
            # response metadata so A2A clients (e.g. the evaluation harness) can collect
            # them per query. The Kyma dashboard uses the streaming conversation API and
            # is unaffected by this field. The protobuf Struct natively represents a JSON
            # object, so the metrics dict is stored directly (no json.dumps / double-decode).
            # Note: Struct stores numbers as doubles, so integer counts round-trip as floats.
            response_metadata = Struct()
            response_metadata.update({"x-metrics": request_metrics.as_dict()})

            response_message = Message(
                role=Role.ROLE_AGENT,
                parts=[Part(text=answer)],
                message_id=message.message_id or "",
                context_id=session_id,
                task_id=message.task_id or "",
                metadata=response_metadata,
            )
            await event_queue.enqueue_event(response_message)

        except HTTPException as exc:
            if is_recorded_http_exception(context, exc):
                # Answered with the HTTP status by the exception handler of the application.
                raise
            logger.error(f"HTTP error in A2A Kyma executor: {exc.detail}")
            raise InternalError(message=str(exc.detail)) from exc
        except K8sClientError as exc:
            logger.error(f"K8s error in A2A Kyma executor: {exc.message}")
            raise InternalError(message=exc.message) from exc
        except InternalError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error in A2A Kyma executor")
            raise InternalError(message="Unexpected error during agent execution") from exc

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel is not supported for this agent.

        Args:
            context: The A2A request context (unused).
            event_queue: Event queue (unused).

        Raises:
            UnsupportedOperationError: Always raised; cancellation is not supported.
        """
        raise UnsupportedOperationError(message="Cancellation is not supported by the Kyma agent")


def build_kyma_a2a_app(base_url: str = "http://localhost:8000/api/agent/kyma") -> Starlette:
    """Build and return the Starlette sub-application for the Kyma A2A agent.

    The sub-app is designed to be mounted at /api/agent/kyma in FastAPI via
    ``app.mount("/api/agent/kyma", build_kyma_a2a_app())``.

    Mounted routes (relative paths within the sub-app):
      GET  /.well-known/agent-card.json  – A2A agent card discovery
      POST /chat                         – A2A JSON-RPC (message/send) endpoint

    Args:
        base_url: The public base URL for the agent card (e.g. advertised
                  endpoint in the agent-card). Override in production via
                  the KYMA_A2A_BASE_URL env var or configuration.

    Returns:
        A Starlette application with the A2A JSON-RPC and agent-card routes.
    """
    skill = AgentSkill(
        id="kyma_chat",
        name="Kyma Agent Chat",
        description=(
            "Answers questions about Kyma and Kubernetes resources, "
            "diagnoses cluster issues, and fetches live cluster state."
        ),
        input_modes=["text/plain"],
        output_modes=["text/plain"],
        tags=["kyma", "kubernetes", "k8s", "cluster"],
        examples=["List all namespaces", "Why is my Kyma Function not starting?"],
    )

    agent_card = AgentCard(
        name="Kyma Companion Agent",
        description="AI assistant for Kyma and Kubernetes cluster management (Joule).",
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        skills=[skill],
        supported_interfaces=[
            AgentInterface(url=f"{base_url}/chat"),
        ],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=KymaAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    routes: list[Route] = []
    routes.extend(create_agent_card_routes(agent_card))
    routes.extend(create_jsonrpc_routes_with_http_status(request_handler, "/chat"))

    app = Starlette(routes=routes)
    return app
