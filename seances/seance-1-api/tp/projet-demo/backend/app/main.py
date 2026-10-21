from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AccesRefuse,
    ConflitReservation,
    DomainError,
    EmailDejaUtilise,
    RessourceIntrouvable,
)
from app.routers import auth, items, reservations

app = FastAPI(title="GearShare API", version="0.1.0")
app.include_router(auth.router)
app.include_router(items.router)
app.include_router(reservations.router)


STATUS_PAR_EXCEPTION: dict[type[DomainError], int] = {
    RessourceIntrouvable: 404,
    ConflitReservation: 409,
    EmailDejaUtilise: 409,
    AccesRefuse: 403,
}


@app.exception_handler(DomainError)
def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    status: int = STATUS_PAR_EXCEPTION.get(type(exc), 400)
    return JSONResponse(status_code=status, content={"detail": exc.message})


@app.get(
    "/health",
    tags=["monitoring"],
    summary="Vérifier que l'API répond",
    description="Sonde de vivacité : ne consulte ni la base ni les services externes.",
)
def health() -> dict[str, str]:
    return {"status": "ok", "message": "GearShare est en forme"}
