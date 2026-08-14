from enum import StrEnum


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    TOO_MANY_REQUESTS = "too_many_requests"
    INTERNAL_ERROR = "internal_error"


class ServiceResponse(dict):
    """Class for standardizing responses in the service layer."""

    def __init__(
        self,
        ok: bool,
        code: ErrorCode | None = None,
        data: dict | list | None = None,
        message: str | None = None,
    ):
        payload = {"ok": ok}
        if data is not None:
            payload["data"] = data
        if code is not None:
            payload["code"] = code
        if message is not None:
            payload["message"] = message
        super().__init__(**payload)


class ErrorResponse(ServiceResponse):
    def __init__(self, message: str, code: ErrorCode):
        super().__init__(ok=False, message=message, code=code)


class SuccessResponse(ServiceResponse):
    def __init__(self, data: dict | list | None = None, message: str | None = None):
        super().__init__(ok=True, data=data, message=message)
