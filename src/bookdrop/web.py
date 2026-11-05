import logging
import shutil
import tomllib
from collections.abc import Callable
from dataclasses import fields
from decimal import Decimal, InvalidOperation
from importlib.metadata import version

import httpx
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment, PackageLoader, select_autoescape

from bookdrop import drops, filing, layout, lookup, metadata, stump
from bookdrop.adept import Refused, prepare
from bookdrop.config import Settings
from bookdrop.executor import Executor, Exists
from bookdrop.lookup import LookupFailed
from bookdrop.metadata import Metadata, normalise_isbn

log = logging.getLogger(__name__)

# The list fields, each edited as one box, and what separates its entries there.
# A genre can contain a comma ("Fiction, fantasy, epic"), so genres go one a line.
LISTS = {"authors": "&", "genres": "\n"}
EDITABLE = tuple(f.name for f in fields(Metadata) if f.name not in LISTS)

templates = Environment(
    loader=PackageLoader("bookdrop"), autoescape=select_autoescape()
)


def problem(meta: Metadata) -> str:
    """Why the book cannot be filed as it stands, or "" when it can."""
    if not meta.title:
        return "A book needs a title."
    if not meta.authors:
        return "A book needs at least one author."
    if meta.isbn and not normalise_isbn(meta.isbn):
        return "The ISBN's check digit is wrong; correct it or clear it."
    if meta.series_index and not meta.series:
        return "A series number needs a series."
    if meta.series_index:
        try:
            number = Decimal(meta.series_index)
        except InvalidOperation:
            number = None
        # Decimal also reads "NaN" and "Infinity".
        if number is None or not number.is_finite() or number < 0:
            return "The series number must be a number, such as 2 or 3.5."
    return ""


def create_app(
    settings: Settings | None = None,
    find: Callable[[str], Metadata | None] | None = None,
    scan: Callable[[], None] | None = None,
) -> FastAPI:
    """The web app. find(isbn) looks an ISBN up, as lookup.open_library does, and
    scan() asks Stump to scan, as stump.scan does; tests replace both."""
    settings = settings or Settings()
    executor = Executor(settings.books_root, settings.dry_run)

    def stump_scan() -> None:
        if not (
            settings.stump_url and settings.stump_api_key and settings.stump_library_id
        ):
            raise stump.ScanFailed("Stump is not set up for bookdrop")
        with httpx.Client() as http:
            stump.scan(
                settings.stump_url,
                settings.stump_api_key,
                settings.stump_library_id,
                http,
            )

    scan = scan or stump_scan

    def open_library(isbn: str) -> Metadata:
        with lookup.client() as http:
            return lookup.open_library(isbn, http)

    find = find or open_library
    app = FastAPI(title="bookdrop")
    aliases_file = settings.data_dir / "authors.toml"

    def render(name: str, status: int = 200, **context) -> HTMLResponse:
        page = templates.get_template(name).render(**context)
        return HTMLResponse(page, status_code=status)

    def load_aliases() -> tuple[dict[str, str], str]:
        try:
            return layout.aliases(aliases_file), ""
        except (tomllib.TOMLDecodeError, OSError) as error:
            return {}, str(error)

    def look_up(record: drops.Drop) -> None:
        """Fill the record's gaps from Open Library, and say what came of it."""
        isbn = record.metadata.isbn
        record.lookup_failed = False
        if not isbn:
            record.lookup = "No ISBN, so Open Library was not asked."
            return
        try:
            found = find(isbn)
        except LookupFailed as error:
            log.warning("Open Library lookup of %s failed: %s", isbn, error)
            record.lookup_failed = True
            record.lookup = (
                f"Open Library could not be asked about {isbn}: {error}. "
                "The gaps below may be ones it would fill; look up again later."
            )
            return
        if found is None:
            record.lookup = f"Open Library has no record of ISBN {isbn}."
            return
        before = set(record.sources)
        record.metadata, record.sources = lookup.fill(
            record.metadata, found, record.sources
        )
        filled = len(set(record.sources) - before)
        record.lookup = (
            f"Open Library filled {filled} field{'' if filled == 1 else 's'}."
            if filled
            else "Open Library had nothing the book lacks."
        )

    def canonicalise(drop: drops.Drop, table: dict[str, str]) -> None:
        authors = layout.canonical(drop.metadata.authors, table)
        if authors != drop.metadata.authors:
            drop.metadata.authors = authors
            drop.sources["authors"] = "alias"

    def file_book(record: drops.Drop) -> str:
        """File a confirmed drop, or in dry run say what filing would write.

        Returns why it could not be filed, or "" when it was (or would be).
        """
        try:
            plan = filing.plan(record)
        except Exception as error:
            log.exception("Preparing %s for filing failed", record.id)
            return f"The book could not be prepared for filing: {error}"
        record.planned = [str(plan.directory / name) for name in plan.files]
        if settings.dry_run:
            return ""
        try:
            executor.file(plan)
        except Exists as error:
            return str(error)
        except OSError as error:
            log.exception("Filing %s into %s failed", record.id, plan.directory)
            return f"The library could not be written to: {error}"
        record.filed = str(plan.directory)
        # The library has the book now; the drop keeps only its record.
        record.book.unlink()
        try:
            scan()
        except stump.ScanFailed as error:
            log.warning(
                "Asking Stump to scan after filing %s failed: %s", record.id, error
            )
            record.scan = (
                f"Stump could not be asked to scan: {error}. "
                "Scan the library from Stump to see the book there."
            )
            record.scan_failed = True
        else:
            record.scan = (
                "Stump is scanning the library; the book appears when it ends."
            )
            record.scan_failed = False
        return ""

    def show(drop: drops.Drop, alias_error: str, reason: str = "") -> HTMLResponse:
        destination = layout.destination(drop.metadata, drop.extension)
        return render(
            "drop.html",
            drop=drop,
            meta=drop.metadata,
            destination=destination,
            dry_run=settings.dry_run,
            exists=not drop.filed
            and (settings.books_root / destination.parent).exists(),
            has_cover=drop.book.exists() and metadata.cover(drop.book) is not None,
            alias_error=alias_error,
            problem=reason,
        )

    @app.get("/healthz")
    def healthz() -> dict[str, str | bool]:
        return {"status": "ok", "dry_run": settings.dry_run}

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return render(
            "index.html",
            version=version("bookdrop"),
            dry_run=settings.dry_run,
            drops=drops.all_drops(settings.data_dir),
        )

    @app.post("/drop")
    def drop(file: UploadFile) -> Response:
        directory = drops.new_directory(settings.data_dir)
        upload = directory / "upload"
        with upload.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        try:
            prepared = prepare(upload, directory, settings.adept_dir)
        except Refused as refused:
            drops.discard(directory)
            return render("refused.html", status=422, reason=str(refused))
        for leftover in directory.iterdir():
            if leftover != prepared.book:
                leftover.unlink()

        own = metadata.read(prepared.book)
        record = drops.Drop(
            directory=directory,
            uploaded_as=file.filename or "upload",
            preparation=prepared.preparation,
            book_name=prepared.book.name,
            metadata=own,
            sources=lookup.fill(own, Metadata())[1],
            created=drops.now(),
        )
        # Synchronous on purpose: the confirmation screen is the next thing the
        # person sees, and lookup's timeout bounds the wait.
        look_up(record)
        canonicalise(record, load_aliases()[0])
        record.save()
        return RedirectResponse(f"/drops/{record.id}", status_code=303)

    @app.get("/drops/{drop_id}", response_class=HTMLResponse)
    def view(drop_id: str) -> HTMLResponse:
        record = drops.load(settings.data_dir, drop_id)
        if record is None:
            return render("refused.html", status=404, reason="No such drop.")
        return show(record, load_aliases()[1])

    @app.post("/drops/{drop_id}", response_class=HTMLResponse)
    async def edit(drop_id: str, request: Request) -> HTMLResponse:
        record = drops.load(settings.data_dir, drop_id)
        if record is None:
            return render("refused.html", status=404, reason="No such drop.")
        if record.filed:
            return show(record, load_aliases()[1])
        form = await request.form()

        def submitted(name: str) -> str:
            return str(form.get(name, "")).strip()

        for name in EDITABLE:
            value = submitted(name)
            if value != getattr(record.metadata, name):
                setattr(record.metadata, name, value)
                record.sources[name] = "you"
        for name, separator in LISTS.items():
            values = [v.strip() for v in submitted(name).split(separator) if v.strip()]
            if values != getattr(record.metadata, name):
                setattr(record.metadata, name, values)
                record.sources[name] = "you"
        if submitted("action") == "lookup":
            look_up(record)
        table, alias_error = load_aliases()
        canonicalise(record, table)
        reason = problem(record.metadata)
        record.confirmed = submitted("action") == "confirm" and not reason
        record.planned = []
        if record.confirmed:
            reason = file_book(record)
            record.confirmed = not reason
        record.save()
        return show(record, alias_error, reason)

    @app.get("/drops/{drop_id}/cover")
    def cover(drop_id: str) -> Response:
        record = drops.load(settings.data_dir, drop_id)
        image = metadata.cover(record.book) if record and record.book.exists() else None
        if image is None:
            return Response(status_code=404)
        return Response(image[0], media_type=image[1])

    return app
