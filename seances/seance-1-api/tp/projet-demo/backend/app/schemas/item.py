from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titre: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    tarif_jour: float = Field(gt=0)
    disponible: bool = True


class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titre: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    tarif_jour: float | None = Field(default=None, gt=0)
    disponible: bool | None = None


class ItemRead(BaseModel):
    id: int
    titre: str
    description: str | None
    tarif_jour: float
    disponible: bool
