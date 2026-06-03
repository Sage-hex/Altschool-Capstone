from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Role = Literal["student", "admin"]


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Role = "student"


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    user: UserOut
    token: str
    token_type: str = "bearer"


class CourseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    code: str = Field(min_length=2, max_length=30)
    capacity: int = Field(gt=0, le=10_000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class CourseUpdate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    code: str = Field(min_length=2, max_length=30)
    capacity: int = Field(gt=0, le=10_000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class CourseOut(BaseModel):
    id: int
    title: str
    code: str
    capacity: int
    is_active: bool
    available_seats: int
    enrollment_count: int
    created_by: int
    created_at: datetime
    updated_at: datetime


class EnrollmentOut(BaseModel):
    id: int
    created_at: datetime
    user_id: int
    user_name: str
    user_email: EmailStr
    course_id: int
    course_title: str
    course_code: str


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
