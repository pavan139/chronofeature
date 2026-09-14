"""Server-rendered, locale-addressable documents. No birth-data persistence."""
from __future__ import annotations
import json
import os
import secrets
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=ROOT / "templates")
ROUTES = {"": "match", "porutham": "porutham", "birth-chart": "chart"}

@lru_cache
def catalogs():
    return {p.stem: json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((ROOT / "locales").glob("*.json"))}

def site_origin():
    raw = os.getenv("SITE_URL", "").rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        return ""
    return raw

def index_locales():
    if os.getenv("INDEXABLE", "false").lower() != "true" or not site_origin():
        return set()
    # Owners opt translated pages into indexing after native-language review.
    return set(os.getenv("INDEX_LOCALES", "en").split(",")) & set(catalogs())

def install_web(app):
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.middleware("http")
    async def response_policy(request: Request, call_next):
        request.state.nonce = secrets.token_urlsafe(18)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; script-src 'self' 'nonce-{request.state.nonce}'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.method == "POST" or request.url.path.startswith(("/places", "/chart", "/match", "/health", "/docs", "/openapi", "/redoc")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        elif request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=3600"
        return response

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/en/", status_code=302)

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest():
        return JSONResponse({
            "name": "Astro · Vedic compatibility",
            "short_name": "Astro",
            "description": "Private-by-design Kundali matching and sidereal birth charts.",
            "start_url": "/en/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#f6f8f8",
            "theme_color": "#142b32",
            "icons": [{"src": "/static/favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}],
        }, media_type="application/manifest+json")

    @app.get("/robots.txt", include_in_schema=False)
    def robots():
        if not index_locales():
            return PlainTextResponse("User-agent: *\nDisallow: /\n")
        lines = ["User-agent: *", "Disallow: /match/", "Disallow: /chart",
                 "Disallow: /places", "Disallow: /docs", "Disallow: /openapi.json",
                 "Disallow: /redoc", "Disallow: /health",
                 "Sitemap: " + site_origin() + "/sitemap.xml"]
        return PlainTextResponse("\n".join(lines) + "\n")

    @app.get("/sitemap.xml", include_in_schema=False)
    def sitemap():
        origin = site_origin()
        urls = [origin + "/" + lang + "/" + (route + "/" if route else "")
                for lang in sorted(index_locales()) for route in ROUTES]
        body = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        body += "".join("<url><loc>" + escape(url) + "</loc></url>" for url in urls)
        return Response(body + "</urlset>", media_type="application/xml")

    def render(request, lang, view):
        messages = catalogs()
        if lang not in messages:
            raise HTTPException(404, "Language not found")
        t = messages[lang]
        route = "" if view == "match" else ("birth-chart/" if view == "chart" else "porutham/")
        origin = site_origin()
        canonical = origin + "/" + lang + "/" + route if origin else None
        indexable = lang in index_locales()
        # Google hreflang accepts supported ISO 639-1 language codes.
        # Other BCP 47 routes remain navigable via the language menu.
        alternates = [{"code": code, "url": origin + "/" + code + "/" + route}
                      for code in sorted(index_locales()) if len(code) == 2] if origin else []
        title = t["chart"] if view == "chart" else ("Dasa Porutham · " + t["title"] if view == "porutham" else t["title"])
        descriptions = {
            "match": t["intro"] + " " + t["note"],
            "porutham": "Dasa Porutham. " + t["intro"] + " " + t["note"],
            "chart": t["chart"] + ". " + t["intro"] + " " + t["note"],
        }
        description = descriptions[view]
        page_id = canonical or "/" + lang + "/" + route
        schema = {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebSite", "@id": (origin + "/#website") if origin else "/#website",
                 "name": "Astro", **({"url": origin + "/"} if origin else {})},
                {"@type": "WebApplication", "@id": page_id + "#app", "name": title,
                 "applicationCategory": "LifestyleApplication", "operatingSystem": "Web",
                 "isAccessibleForFree": True, "inLanguage": lang, "description": description,
                 "featureList": ["Ashtakoota", "Dasa Porutham", "Sidereal birth chart", "Vimshottari dasha"],
                 **({"url": canonical} if canonical else {})},
                {"@type": "WebPage", "@id": page_id + "#page", "name": title,
                 "description": description, "inLanguage": lang,
                 "isPartOf": {"@id": (origin + "/#website") if origin else "/#website"},
                 "mainEntity": {"@id": page_id + "#app"},
                 **({"url": canonical} if canonical else {})},
            ],
        }
        response = TEMPLATES.TemplateResponse(request=request, name="page.html", context={
            "t": t, "languages": list(messages.values()), "lang": lang, "view": view,
            "title": title, "description": description, "og_locale": lang.replace("-", "_") + "_IN",
            "canonical": canonical, "alternates": alternates,
            "indexable": indexable, "route": route, "nonce": request.state.nonce,
            "schema": schema,
        })
        response.headers["Content-Language"] = lang
        response.headers["X-Robots-Tag"] = "index, follow" if indexable else "noindex, follow"
        return response

    @app.get("/{lang}/", response_class=HTMLResponse, include_in_schema=False)
    def home(request: Request, lang: str):
        return render(request, lang, "match")

    @app.get("/{lang}/{page}/", response_class=HTMLResponse, include_in_schema=False)
    def page(request: Request, lang: str, page: str):
        if page not in ROUTES:
            raise HTTPException(404, "Page not found")
        return render(request, lang, ROUTES[page])
