from enum import StrEnum


class ErrorCode(StrEnum):
    NOT_FOUND = "not_found"
    VALIDATION_ERROR = "validation_error"
    INTERNAL_ERROR = "internal_error"


class ServiceResponse(dict):
    """Class for standardizing responses in the service layer."""

    def __init__(
        self,
        ok: bool,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        data: dict | list | None = None,
        message: str | None = None,
    ):
        payload = {"ok": ok, "code": code}
        if data is not None:
            payload["data"] = data
        if message is not None:
            payload["message"] = message
        super().__init__(**payload)


class ErrorResponse(ServiceResponse):
    def __init__(self, message: str, code: ErrorCode):
        super().__init__(ok=False, message=message, code=code)


class SuccessResponse(ServiceResponse):
    def __init__(self, data: dict | list | None = None):
        super().__init__(ok=True, data=data)
