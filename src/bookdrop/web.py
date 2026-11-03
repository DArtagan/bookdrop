import shutil
import uuid
from html import escape
from importlib.metadata import version

from fastapi import FastAPI, UploadFile
from fastapi.responses import HTMLResponse

from bookdrop.adept import Refused, prepare
from bookdrop.config import Settings


def _page(body: str) -> str:
    return (
        "<!doctype html><meta name=viewport content='width=device-width'>"
        f"<title>bookdrop</title>{body}"
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="bookdrop")

    @app.get("/healthz")
    def healthz() -> dict[str, str | bool]:
        return {"status": "ok", "dry_run": settings.dry_run}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        mode = (
            "Dry run: books are prepared and nothing in the library is changed."
            if settings.dry_run
            else "Filing is live."
        )
        return _page(
            f"<h1>bookdrop {escape(version('bookdrop'))}</h1>"
            f"<p>{escape(mode)}</p>"
            "<form method=post action=/drop enctype=multipart/form-data>"
            "<input type=file name=file accept='.acsm,.epub,.pdf' required> "
            "<button>Drop</button></form>"
        )

    @app.post("/drop", response_class=HTMLResponse)
    def drop(file: UploadFile) -> HTMLResponse:
        drop_dir = settings.data_dir / "drops" / uuid.uuid4().hex
        drop_dir.mkdir(parents=True)
        upload = drop_dir / "upload"
        with upload.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        try:
            book = prepare(upload, drop_dir, settings.adept_dir)
        except Refused as refused:
            shutil.rmtree(drop_dir)
            return HTMLResponse(
                _page(f"<h1>Not taken</h1><p>{escape(str(refused))}</p>"),
                status_code=422,
            )
        for leftover in drop_dir.iterdir():
            if leftover != book:
                leftover.unlink()
        size = book.stat().st_size / 1_000_000
        name = escape(file.filename or "upload")
        return HTMLResponse(
            _page(
                f"<h1>Ready</h1><p>{name} is a DRM-free "
                f"{book.suffix[1:].upper()}, {size:.1f} MB.</p>"
            )
        )

    return app
