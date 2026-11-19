"""Answer selected errors of the A2A executor with an HTTP status instead of a JSON-RPC error.

For v0.3 requests (`message/send`) the A2A SDK converts every exception of the executor
into a JSON-RPC error with HTTP status 200. Errors that the legacy conversations API
returned as HTTP status (for example 401, 403, 429) are therefore recorded by the
executor in the call context with `record_http_exception` and raised again by a wrapper
around the JSON-RPC endpoint, so that the exception handler of the application answers
with the HTTP status. For v1.0 requests (`SendMessage`) the SDK already lets an
`HTTPException` of the executor propagate; the wrapper does not change that.

The wrapper inspects the call context after the endpoint returned and before the response
is sent. It does not apply to streaming responses, whose executor runs while the response
is sent; the agent card does not offer streaming.
"""

from collections.abc import Awaitable, Callable

from a2a.server.agent_execution import RequestContext
from a2a.server.context import ServerCallContext
from a2a.server.request_handlers import RequestHandler
from a2a.server.routes import create_jsonrpc_routes
from a2a.server.routes.common import DefaultServerCallContextBuilder
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

# Key in the A2A call context state for an HTTPException that must reach the client as HTTP status.
HTTP_EXCEPTION_STATE_KEY = "http_exception"


def record_http_exception(context: RequestContext, exc: HTTPException) -> None:
    """Record the exception, so that the client receives its HTTP status."""
    context.call_context.state[HTTP_EXCEPTION_STATE_KEY] = exc


def is_recorded_http_exception(context: RequestContext, exc: HTTPException) -> bool:
    """Return whether the exception was recorded with `record_http_exception`."""
    return context.call_context.state.get(HTTP_EXCEPTION_STATE_KEY) is exc


class _CallContextBuilder(DefaultServerCallContextBuilder):
    """Builds the call context and keeps it on the request for `_raise_recorded_http_exception`."""

    def build(self, request: Request) -> ServerCallContext:
        """Build the ServerCallContext and store it in the request state."""
        call_context = super().build(request)
        request.state.call_context = call_context
        return call_context


def _raise_recorded_http_exception(
    endpoint: Callable[[Request], Awaitable[Response]],
) -> Callable[[Request], Awaitable[Response]]:
    """Wrap the JSON-RPC endpoint to raise the HTTPException recorded by the executor."""

    async def wrapper(request: Request) -> Response:
        response = await endpoint(request)
        call_context = getattr(request.state, "call_context", None)
        exc = call_context.state.get(HTTP_EXCEPTION_STATE_KEY) if call_context else None
        if exc is not None:
            raise exc
        return response

    return wrapper


def create_jsonrpc_routes_with_http_status(request_handler: RequestHandler, rpc_url: str) -> list[Route]:
    """Create the A2A JSON-RPC routes (v1.0 and v0.3) that answer recorded exceptions with their HTTP status."""
    return [
        Route(route.path, _raise_recorded_http_exception(route.endpoint), methods=["POST"])
        for route in create_jsonrpc_routes(
            request_handler, rpc_url, context_builder=_CallContextBuilder(), enable_v0_3_compat=True
        )
    ]
