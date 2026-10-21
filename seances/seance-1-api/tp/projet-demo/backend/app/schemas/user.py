from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=2, max_length=80)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    # pas de password_hash ici


class OwnerRead(BaseModel):
    """Le propriétaire vu depuis un item : ni email ni password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str


class TokenRead(BaseModel):
    access_token: str
    token_type: str
    expires_in: int   # durée de validité, en secondes
