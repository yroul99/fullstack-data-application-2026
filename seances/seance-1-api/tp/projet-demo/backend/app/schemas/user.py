from pydantic import BaseModel, ConfigDict


class OwnerRead(BaseModel):
    """Le propriétaire vu depuis un item : ni email ni password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
