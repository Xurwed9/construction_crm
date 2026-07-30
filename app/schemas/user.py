import uuid

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    password: str | None = None


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    is_active: bool

    model_config = {"from_attributes": True}
