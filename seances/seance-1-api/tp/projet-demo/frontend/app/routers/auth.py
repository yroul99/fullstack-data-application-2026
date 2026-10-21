from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.api_client import ApiError, api_client
from app.auth import COOKIE_JETON, COOKIE_SECURE
from app.templating import templates

router = APIRouter()


def chemin_local(cible: str | None) -> str:
    """N'autorise qu'une redirection vers une page de ce site."""
    if cible and cible.startswith("/") and not cible.startswith(("//", "/\\")):
        return cible
    return "/items"


# --- Connexion -------------------------------------------------------------------


@router.get("/connexion", response_class=HTMLResponse)
def connexion_page(request: Request, suivant: str | None = None) -> HTMLResponse:
    return templates.TemplateResponse(request, "auth/connexion.html", {"suivant": suivant})


@router.post("/connexion")
def connexion(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    suivant: Annotated[str | None, Form()] = None,
) -> Response:
    try:
        jeton = api_client.login(email, password)
    except ApiError as exc:
        if exc.status_code != 401:
            raise
        return templates.TemplateResponse(
            request,
            "auth/connexion.html",
            {"erreur": "Email ou mot de passe incorrect.", "saisie": {"email": email}, "suivant": suivant},
            status_code=401,
        )
    response = RedirectResponse(chemin_local(suivant), status_code=303)
    response.set_cookie(
        COOKIE_JETON,
        jeton["access_token"],
        max_age=jeton["expires_in"],
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    return response


@router.post("/deconnexion")
def deconnexion() -> Response:
    response = RedirectResponse("/items", status_code=303)
    response.delete_cookie(COOKIE_JETON)
    return response


# --- Inscription -----------------------------------------------------------------


@router.get("/inscription", response_class=HTMLResponse)
def inscription_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "auth/inscription.html", {})


@router.post("/inscription")
def inscription(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    display_name: Annotated[str, Form()],
) -> Response:
    try:
        api_client.register(email, password, display_name)
    except ApiError as exc:
        if exc.status_code == 409:
            erreurs = ["Un compte existe déjà avec cet email."]
        elif exc.status_code == 422:
            erreurs = exc.messages()
        else:
            raise
        return templates.TemplateResponse(
            request,
            "auth/inscription.html",
            {"erreurs": erreurs, "saisie": {"email": email, "display_name": display_name}},
            status_code=exc.status_code,
        )
    return RedirectResponse("/connexion?inscription=ok", status_code=303)
