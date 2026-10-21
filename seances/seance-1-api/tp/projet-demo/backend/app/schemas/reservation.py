from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: int = Field(ge=1)
    date_debut: date
    date_fin: date

    @model_validator(mode="after")
    def check_dates(self) -> "ReservationCreate":
        if self.date_fin <= self.date_debut:
            raise ValueError("date_fin doit être postérieure à date_debut")
        return self


class ReservationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statut: Literal["annulee"]


class ReservationRead(BaseModel):
    id: int
    item_id: int
    date_debut: date
    date_fin: date
    statut: Literal["active", "annulee"]
