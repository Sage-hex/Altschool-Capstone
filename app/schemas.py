from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    user: UserOut
    token: str
    token_type: str = "bearer"


class CourseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=10, max_length=1000)
    instructor: str = Field(min_length=2, max_length=100)
    capacity: int = Field(ge=1, le=10_000)


class CourseOut(BaseModel):
    id: int
    title: str
    description: str
    instructor: str
    capacity: int
    available_seats: int
    enrollment_count: int
    created_by: int
    created_at: datetime
    updated_at: datetime


class EnrollmentOut(BaseModel):
    id: int
    status: Literal["active", "cancelled"]
    enrolled_at: datetime
    updated_at: datetime
    user_id: int
    user_name: str
    user_email: EmailStr
    course_id: int
    course_title: str
    course_instructor: str


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
