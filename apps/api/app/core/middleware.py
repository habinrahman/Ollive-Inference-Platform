from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_context import request_id_var, trace_id_var

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        trace_id = request.headers.get("x-trace-id") or request_id
        request_token = request_id_var.set(request_id)
        trace_token = trace_id_var.set(trace_id)
        started = perf_counter()

        try:
            response = await call_next(request)
            return response
        except Exception:
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            raise
        finally:
            latency_ms = int((perf_counter() - started) * 1000)
            status_code = locals().get("response").status_code if "response" in locals() else 500
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                },
            )
            if "response" in locals():
                response.headers["x-request-id"] = request_id
                response.headers["x-trace-id"] = trace_id
            request_id_var.reset(request_token)
            trace_id_var.reset(trace_token)
