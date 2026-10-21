from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api_client import ApiError
from app.auth import COOKIE_JETON
from app.routers import auth, items, reservations
from app.templating import BASE_DIR, templates

app = FastAPI(title="GearShare — frontend")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(auth.router)
app.include_router(items.router)
app.include_router(reservations.router)


@app.exception_handler(ApiError)
def api_error_page(request: Request, exc: ApiError) -> Response:
    if exc.status_code == 401:
        cible = "/connexion"
        if request.method == "GET":
            cible += "?" + urlencode({"suivant": request.url.path})
        response = RedirectResponse(cible, status_code=303)
        response.delete_cookie(COOKIE_JETON)
        return response
    messages = {
        403: "Vous n'avez pas le droit de faire cette action.",
        404: "Cette page n'existe pas ou plus.",
        503: "Le service est momentanément indisponible. Réessayez dans un instant.",
    }
    message = messages.get(exc.status_code, "Une erreur est survenue.")
    return templates.TemplateResponse(
        request, "erreur.html", {"message": message}, status_code=exc.status_code
    )


@app.get("/", include_in_schema=False)
def accueil() -> RedirectResponse:
    return RedirectResponse("/items")
