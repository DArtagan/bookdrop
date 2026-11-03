import re
from datetime import datetime
from importlib.metadata import version

import httpx

from bookdrop.metadata import Metadata

OPEN_LIBRARY = "https://openlibrary.org"
# Open Library answers in about four seconds from the cluster, and a lookup is up
# to five requests; a slower one leaves gaps rather than holding the upload.
TIMEOUT = 8.0
MAX_AUTHORS = 3

# "The Stormlight Archive ; bk. 1", "Dune (2)", "Discworld, #4": a name, then a
# trailing number with an optional word for it.
SERIES = re.compile(
    r"^(?P<name>.+?)[\s,;:(#-]+(?:bk\.?|book|vol\.?|v\.|no\.?|part)?\s*"
    r"(?P<index>\d+(?:\.\d+)?)\)?\s*$",
    re.IGNORECASE,
)
DATE_FORMATS = ("%b %d, %Y", "%B %d, %Y", "%d %B %Y", "%B %Y", "%Y-%m-%d", "%Y")


def client() -> httpx.Client:
    return httpx.Client(
        base_url=OPEN_LIBRARY,
        timeout=TIMEOUT,
        follow_redirects=True,
        headers={
            "User-Agent": f"bookdrop/{version('bookdrop')} "
            "(+https://github.com/DArtagan/bookdrop)"
        },
    )


def open_library(isbn: str, http: httpx.Client) -> Metadata:
    """What Open Library knows of an ISBN; empty when it knows nothing or fails."""
    try:
        edition = _get(http, f"/isbn/{isbn}.json")
        if edition is None:
            return Metadata()
        work = None
        if works := edition.get("works"):
            work = _get(http, f"{works[0]['key']}.json")
        author_keys = [a["key"] for a in edition.get("authors", []) if "key" in a]
        if not author_keys and work:
            author_keys = [
                a["author"]["key"] for a in work.get("authors", []) if "author" in a
            ]
        authors = []
        for key in author_keys[:MAX_AUTHORS]:
            if (author := _get(http, f"{key}.json")) and author.get("name"):
                authors.append(author["name"])
    except httpx.HTTPError, ValueError, KeyError, TypeError:
        return Metadata()
    series, index = _series(edition.get("series") or [])
    description = (work or {}).get("description") or edition.get("description") or ""
    if isinstance(description, dict):
        description = description.get("value", "")
    languages = edition.get("languages") or [{}]
    return Metadata(
        title=edition.get("title", ""),
        authors=authors,
        series=series,
        series_index=index,
        isbn=isbn,
        publisher=(edition.get("publishers") or [""])[0],
        date=_date(edition.get("publish_date", "")),
        description=description.strip(),
        language=languages[0].get("key", "").rsplit("/", 1)[-1],
    )


def fill(book: Metadata, found: Metadata) -> tuple[Metadata, dict[str, str]]:
    """The book's own values, gaps filled from found, and where each came from."""
    merged, sources = {}, {}
    for name, own in book.to_dict().items():
        other = found.to_dict()[name]
        if own:
            merged[name], sources[name] = own, "book"
        elif other:
            merged[name], sources[name] = other, "Open Library"
        else:
            merged[name] = own
    return Metadata.from_dict(merged), sources


def _get(http: httpx.Client, path: str) -> dict | None:
    response = http.get(path)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def _series(entries: list[str]) -> tuple[str, str]:
    if not entries:
        return "", ""
    entry = entries[0].strip()
    if match := SERIES.match(entry):
        return match["name"].strip(), match["index"]
    return entry, ""


def _date(text: str) -> str:
    text = text.strip()
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if fmt == "%Y":
            return f"{parsed:%Y}"
        if fmt == "%B %Y":
            return f"{parsed:%Y-%m}"
        return f"{parsed:%Y-%m-%d}"
    return text
