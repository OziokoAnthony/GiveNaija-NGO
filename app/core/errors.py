import uuid
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppException(StarletteHTTPException):
    """
    Standard application exception to raise from service or domain layer.
    Carries an explicit error code and message.
    """
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message


def get_request_id(request: Request) -> str:
    """Retrieve request ID set by middleware or generate a fallback."""
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def format_error_response(code: str, message: str, request_id: str, status_code: int) -> JSONResponse:
    """
    Builds the uniform API error response required by the Capstone design standards:
    {"error": {"code": "...", "message": "...", "request_id": "..."}}
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register uniform exception handlers on the FastAPI application instance."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        request_id = get_request_id(request)
        return format_error_response(
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            status_code=exc.status_code,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = get_request_id(request)
        # Derive human-readable error code based on status code
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "UNPROCESSABLE_ENTITY",
            429: "RATE_LIMITED",
            500: "INTERNAL_SERVER_ERROR",
        }
        code = code_map.get(exc.status_code, "ERROR")
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return format_error_response(
            code=code,
            message=message,
            request_id=request_id,
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = get_request_id(request)
        # Format Pydantic validation errors into a clean string
        errors = []
        for err in exc.errors():
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            errors.append(f"{loc}: {msg}")
        joined_msg = "; ".join(errors) if errors else "Invalid request data"
        return format_error_response(
            code="VALIDATION_ERROR",
            message=joined_msg,
            request_id=request_id,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = get_request_id(request)
        return format_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
            request_id=request_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
