"""Fixed-template, in-memory PDFs. No caller HTML, URLs, files or persistence."""
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import HTTPException
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .web import catalogs
from .knowledge import TERMS, term_key

ROOT = Path(__file__).parent
PDF_SLOTS = BoundedSemaphore(2)
ENV = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))


def validate_locale(locale):
    if locale not in catalogs():
        raise HTTPException(422, "Unsupported report language")


def deny_resource(url, *args, **kwargs):
    # No renderer network requests, local-file reads, data URLs or attachments.
    raise ValueError("External PDF resources are disabled")


@lru_cache(maxsize=1)
def report_css():
    return (ROOT / "static" / "report.css").read_text(encoding="utf-8")


def report_html(data, births, mode, locale, ayanamsa):
    validate_locale(locale)
    t = catalogs()[locale]
    charts = list(data.get("full_charts", {}).values()) if mode == "match" else [data]
    return ENV.get_template("report.html").render(
        t=t, lang=locale, mode=mode, data=data, births=births, charts=charts,
        ayanamsa=ayanamsa, generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        css=report_css(), title=t["title"] if mode == "match" else t["chart"],
        terms=TERMS, term_key=term_key,
    )


def render_pdf(data, births, mode, locale, ayanamsa):
    if not PDF_SLOTS.acquire(blocking=False):
        raise HTTPException(429, "PDF generation is busy. Try again shortly.", headers={"Retry-After": "5"})
    try:
        from weasyprint import HTML
        document = report_html(data, births, mode, locale, ayanamsa)
        content = HTML(string=document, url_fetcher=deny_resource).write_pdf()
        return Response(content, media_type="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="astro-{mode}.pdf"',
            "Cache-Control": "no-store, private", "X-Robots-Tag": "noindex, nofollow",
            "Content-Language": locale,
        })
    finally:
        PDF_SLOTS.release()
