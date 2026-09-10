"""Request correlation ID and standard error envelope middleware for FastAPI."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"


def format_error_envelope(
    message: str,
    status_code: int,
    correlation_id: str,
    details: Optional[Any] = None,
) -> Dict[str, Any]:
    """Standardized error envelope preserving 'detail' for legacy clients."""
    return {
        "detail": message,
        "error": {
            "code": status_code,
            "message": message,
            "correlation_id": correlation_id,
            "details": details,
        },
    }


import time
from pple.core.logging import log_event, set_correlation_id


def setup_observability_and_errors(app: FastAPI) -> None:
    """Attaches correlation ID middleware and standardized error handlers to FastAPI app."""

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        # Read from incoming header or generate fresh UUID
        corr_id = (
            request.headers.get(CORRELATION_ID_HEADER)
            or request.headers.get(REQUEST_ID_HEADER)
            or str(uuid.uuid4())
        )
        request.state.correlation_id = corr_id
        set_correlation_id(corr_id)
        start_time = time.time()

        try:
            response: Response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = corr_id
            response.headers[REQUEST_ID_HEADER] = corr_id
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            log_event(
                event="http_request",
                logger_name="pple.http",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=elapsed_ms,
            )
            return response
        finally:
            set_correlation_id(None)


    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        corr_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        payload = format_error_envelope(
            message=str(exc.detail),
            status_code=exc.status_code,
            correlation_id=corr_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload,
            headers={
                CORRELATION_ID_HEADER: corr_id,
                REQUEST_ID_HEADER: corr_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        corr_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        message = "Unprocessable Entity / Validation Error"
        payload = format_error_envelope(
            message=message,
            status_code=422,
            correlation_id=corr_id,
            details=exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content=payload,
            headers={
                CORRELATION_ID_HEADER: corr_id,
                REQUEST_ID_HEADER: corr_id,
            },
        )
