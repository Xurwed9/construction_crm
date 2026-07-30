from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=7, max_length=20)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str
