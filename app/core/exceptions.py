"""Domain errors raised by the service layer and mapped to HTTP responses in main.py."""


class DomainError(Exception):
    status_code = 400
    detail: object = "Bad request"
    headers: dict | None = None

    def __init__(self, detail: object | None = None):
        if detail is not None:
            self.detail = detail
        super().__init__(str(self.detail))


class BadRequestError(DomainError):
    status_code = 400


class UnauthorizedError(DomainError):
    status_code = 401
    detail = "Not authenticated"
    headers = {"WWW-Authenticate": "Bearer"}


class ForbiddenError(DomainError):
    status_code = 403
    detail = "Forbidden"


class NotFoundError(DomainError):
    status_code = 404
    detail = "Not found"


class ConflictError(DomainError):
    status_code = 409
    detail = "Conflict"


class UnprocessableError(DomainError):
    status_code = 422
    detail = "Unprocessable request"
