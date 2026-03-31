from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

    class Config:
        from_attributes = True


class SuccessResponse(BaseResponse[Any]):
    def __init__(self, data: Any = None, message: str = "success", code: int = 200):
        super().__init__(code=code, message=message, data=data)


class ErrorResponse(BaseResponse[None]):
    def __init__(self, message: str = "error", code: int = 500):
        super().__init__(code=code, message=message, data=None)


class ResponseCode:
    SUCCESS = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_ERROR = 500
