from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=4, max_length=200)

    @field_validator("username", "password")
    @classmethod
    def strip_values(cls, value: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError("Los campos no pueden estar vacíos.")
        return clean_value


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    role: Literal["admin", "user"]
    username: str
    expires_in_seconds: int = Field(ge=1)


class CurrentUserResponse(BaseModel):
    username: str
    role: Literal["admin", "user"]
