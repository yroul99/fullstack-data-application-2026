from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import ReservationConflict
from app.routers import items, reservations

app = FastAPI(title="GearShare API", version="0.1.0")
app.include_router(items.router)
app.include_router(reservations.router)


@app.exception_handler(ReservationConflict)
def reservation_conflict_handler(request: Request, exc: ReservationConflict) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": exc.message, "reservation_id": exc.reservation_id},
    )


@app.get(
    "/health",
    tags=["monitoring"],
    summary="Vérifier que l'API répond",
    description="Sonde de vivacité : ne consulte ni la base ni les services externes.",
)
def health() -> dict[str, str]:
    return {"status": "ok", "message": "GearShare est en forme"}
