"""Unit tests for answering recorded A2A executor errors with their HTTP status."""

from http import HTTPStatus

import pytest
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface
from a2a.types.a2a_pb2 import Message, Part, Role
from fastapi import HTTPException
from starlette.applications import Starlette
from starlette.testclient import TestClient

from main import custom_http_exception_handler
from routers.a2a_http_status import create_jsonrpc_routes_with_http_status, record_http_exception

_REQUESTS = [
    ("message/send", {"role": "user", "parts": [{"kind": "text", "text": "q"}], "messageId": "m"}, {}),
    ("SendMessage", {"role": "ROLE_USER", "parts": [{"text": "q"}], "messageId": "m"}, {"A2A-Version": "1.0"}),
]


class _Executor(AgentExecutor):
    """Executor whose behaviour is selected by the query text."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input()
        if query == "recorded":
            exc = HTTPException(status_code=HTTPStatus.TOO_MANY_REQUESTS, detail={"error": "limit"})
            record_http_exception(context, exc)
            raise exc
        if query == "not recorded":
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="not recorded")
        await event_queue.enqueue_event(
            Message(role=Role.ROLE_AGENT, parts=[Part(text="answer")], message_id="r", context_id=context.context_id)
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Not supported."""


@pytest.fixture
def client() -> TestClient:
    card = AgentCard(
        name="test",
        description="test",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False),
        supported_interfaces=[AgentInterface(url="http://localhost/chat")],
    )
    handler = DefaultRequestHandler(agent_executor=_Executor(), task_store=InMemoryTaskStore(), agent_card=card)
    app = Starlette(routes=create_jsonrpc_routes_with_http_status(handler, "/chat"))
    app.add_exception_handler(HTTPException, custom_http_exception_handler)  # type: ignore[arg-type]
    return TestClient(app)


def _send(client: TestClient, method: str, message: dict, headers: dict, text: str):
    message = {**message, "parts": [{**message["parts"][0], "text": text}]}
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": {"message": message}}
    return client.post("/chat", json=body, headers=headers)


@pytest.mark.parametrize("method, message, headers", _REQUESTS)
def test_recorded_exception_is_answered_with_its_http_status(client, method, message, headers):
    response = _send(client, method, message, headers, "recorded")

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert response.json() == {"error": "limit"}


def test_not_recorded_exception_of_v03_request_is_a_json_rpc_error(client):
    method, message, headers = _REQUESTS[0]

    response = _send(client, method, message, headers, "not recorded")

    assert response.status_code == HTTPStatus.OK
    assert "error" in response.json()


@pytest.mark.parametrize("method, message, headers", _REQUESTS)
def test_recorded_exception_does_not_affect_the_next_request(client, method, message, headers):
    assert _send(client, method, message, headers, "recorded").status_code == HTTPStatus.TOO_MANY_REQUESTS

    response = _send(client, method, message, headers, "hello")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["result"]
