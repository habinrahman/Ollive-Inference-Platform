from __future__ import annotations

from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


def get_request_id() -> str | None:
    return request_id_var.get()


def get_trace_id() -> str | None:
    return trace_id_var.get()
