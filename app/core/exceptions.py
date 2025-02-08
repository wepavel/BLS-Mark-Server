from enum import Enum
import json
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorResponse(BaseModel):
    code: int
    msg: str
    details: dict[str, Any] = Field(default_factory=dict)
    redirect: bool = False
    notification: bool = False
    custom: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in self.model_fields}


class ErrorCode(Enum):
    #  4000: Bad Request
    BadRequest = ErrorResponse(code=4000, msg='Bad Request')
    #  4021 - 4040: User Management Errors
    CouldNotValidateUserCreds = ErrorResponse(code=4021, msg='Could not validate credentials: ValidationError')
    UserExpiredSignatureError = ErrorResponse(code=4022, msg='Could not validate credentials: ExpiredSignatureError')
    IncorrUserCreds = ErrorResponse(code=4023, msg='Incorrect login or password')
    NotAuthenticated = ErrorResponse(code=4030, msg='Not authenticated')
    InactiveUser = ErrorResponse(code=4032, msg='Inactive user')
    UserRegistrationForbidden = ErrorResponse(code=4033, msg='Open user registration is forbidden on this server')
    UserNotExists = ErrorResponse(code=4035, msg='The user with this username does not exist in the system')
    UserExists = ErrorResponse(code=4036, msg='The user already exists in the system')
    #  4041 - 4060: Project Management Errors
    ProjectLocked = ErrorResponse(code=4041, msg='Project locked')
    AvailableProjectsLimitExceeded = ErrorResponse(code=4042, msg='Available projects limit exceeded')
    AvailableEditsLimitExceeded = ErrorResponse(code=4043, msg='Available edits limit exceeded')
    NameAlreadyExists = ErrorResponse(code=4044, msg='This name already exists')
    InstrumentalTrackExists = ErrorResponse(code=4045, msg='Instrumental track already exists')
    #  4061 - 4081: Task Management Errors
    TaskNotFound = ErrorResponse(code=4061, msg='Task not found')
    TaskAlreadyExists = ErrorResponse(code=4062, msg='Task already exists')
    SessionNotFound = ErrorResponse(code=4071, msg='Session not found')
    SessionAlreadyExists = ErrorResponse(code=4072, msg='Session already exists')
    GTINNotExists = ErrorResponse(code=4073, msg='GTIN not found')
    GTINAlreadyExists = ErrorResponse(code=4073, msg='GTIN already exists')
    #  4301 - 4320: Resource and Limit Errors
    TooManyRequestsError = ErrorResponse(code=4301, msg='Too Many Requests')
    #  4400: Validation Error
    ValidationError = ErrorResponse(code=4400, msg='Validation error')
    #  4401-4500: General Validation Errors
    WrongFormat = ErrorResponse(code=4411, msg='Wrong format')
    DMCodeValidationError = ErrorResponse(code=4412, msg='DMCode validation error')
    GTINValidationError = ErrorResponse(code=4413, msg='GTIN validation error')
    DMCodeAddingError = ErrorResponse(code=4414, msg='DMCode adding error')
    GTINAddingError = ErrorResponse(code=4415, msg='GTIN adding error')
    #  4501 - 4508: API and Request Errors
    Unauthorized = ErrorResponse(
        code=4501, msg='Sorry, you are not allowed to access this service: UnauthorizedRequest'
    )
    AuthorizeError = ErrorResponse(code=4502, msg='Authorization error')
    ForbiddenError = ErrorResponse(code=4503, msg='Forbidden')
    NotFoundError = ErrorResponse(code=4504, msg='Not Found')
    ResponseProcessingError = ErrorResponse(code=4505, msg='Response Processing Error')
    YookassaApiError = ErrorResponse(code=4511, msg='Yookassa Api Error')
    #  5000: Internal Server Error
    InternalError = ErrorResponse(code=5000, msg='Internal Server Error')
    CoreOffline = ErrorResponse(code=5021, msg='Core is offline')
    CoreFileUploadingError = ErrorResponse(code=5022, msg='Core file uploading error')
    #  5041-5060: Database Errors
    DbError = ErrorResponse(code=5041, msg='Bad Gateway')
    #  5061 - 5999: System and Server Errors

    def as_dict(self) -> dict[str, Any]:
        return self.value.as_dict()


HTTP_2_CUSTOM_ERR: dict[int, ErrorResponse] = {
    422: ErrorResponse(code=4400, msg='Validation error', custom=False),
}


class EXC(HTTPException):
    def __init__(
        self,
        exc: ErrorCode,
        details: dict[str, Any] = {},
        redirect: bool = False,
        notification: bool = False,
        headers: dict[str, str] | None = None,
    ) -> None:

        error_response = exc.value.model_copy(
            update={'details': details, 'redirect': redirect, 'notification': notification}
        )

        super().__init__(status_code=400, detail=error_response.model_dump_json(), headers=headers)


def exception_handler(app: FastAPI) -> None:
    def create_error_response(error_response: ErrorResponse) -> JSONResponse:
        details = error_response.details.copy()
        redirect = details.pop('redirect', error_response.redirect)
        notification = details.pop('notification', error_response.notification)

        if details.get('reason') is None:
            details.pop('reason', None)

        if error_response.custom:
            inner_code = error_response.code
        elif error_response.code in HTTP_2_CUSTOM_ERR:
            custom_error = HTTP_2_CUSTOM_ERR[error_response.code]
            inner_code = custom_error.code
            error_response.msg = custom_error.msg
        else:
            inner_code = 5999

        status_code = 400 if 4000 <= inner_code < 5000 else 500

        return JSONResponse(
            status_code=status_code,
            content=jsonable_encoder(
                {
                    'msg': error_response.msg,
                    'code': inner_code,
                    'details': details,
                    'redirect': redirect,
                    'notification': notification,
                }
            ),
        )

    def parse_error_detail(detail: str | dict) -> ErrorResponse:
        if isinstance(detail, str):
            try:
                error_dict = json.loads(detail)
            except json.JSONDecodeError:
                error_dict = {'msg': detail, 'code': 5000, 'custom': False}
        else:
            error_dict = detail

        return ErrorResponse(**error_dict)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        error = parse_error_detail(exc.detail)
        error.details['endpoint'] = request.url.path
        return create_error_response(error)

    @app.exception_handler(StarletteHTTPException)
    async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
        error = parse_error_detail(exc.detail)
        error.details['endpoint'] = request.url.path
        return create_error_response(error)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        error = ErrorCode.ValidationError.value
        error.details = {
            'endpoint': request.url.path,
            'errors': exc.errors(),
        }
        return create_error_response(error)
