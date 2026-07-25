"""Auth and setup schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SetupStatusData(BaseModel):
    initialized: bool


class SetupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="管理员", min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginData(BaseModel):
    user: UserPublic
