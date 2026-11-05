import re
from datetime import datetime
from importlib.metadata import version

import httpx

from bookdrop.metadata import Metadata

OPEN_LIBRARY = "https://openlibrary.org"
# Open Library answers in about four seconds from the cluster, and a lookup is two
# requests; a slower one leaves gaps rather than holding the upload.
TIMEOUT = 8.0

# "The Stormlight Archive ; bk. 1", "Dune (2)", "Discworld, #4": a name, then a
# trailing number with an optional word for it.
SERIES = re.compile(
    r"^(?P<name>.+?)[\s,;:(#-]+(?:bk\.?|book|vol\.?|v\.|no\.?|part)?\s*"
    r"(?P<index>\d+(?:\.\d+)?)\)?\s*$",
    re.IGNORECASE,
)
DATE_FORMATS = ("%b %d, %Y", "%B %d, %Y", "%d %B %Y", "%B %Y", "%Y-%m-%d", "%Y")


def client() -> httpx.Client:
    # Open Library asks clients to name themselves. It also asks frequent ones,
    # making several calls a minute, for a contact address; a drop is about two
    # calls per book bought, so the repository stands in for one.
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
    """What Open Library knows of an ISBN; empty when it knows nothing or fails.

    Never authors: the edition links each by key, a request apiece, and every EPUB
    in the library names its own (230 of 230 on 2026-11-05), which fill keeps.
    """
    try:
        edition = _get(http, f"/isbn/{isbn}.json")
        if edition is None:
            return Metadata()
        work = None
        if works := edition.get("works"):
            work = _get(http, f"{works[0]['key']}.json")
    except httpx.HTTPError, ValueError, KeyError, TypeError:
        return Metadata()
    series, index = _series(edition.get("series") or [])
    description = (work or {}).get("description") or edition.get("description") or ""
    if isinstance(description, dict):
        description = description.get("value", "")
    languages = edition.get("languages") or [{}]
    return Metadata(
        title=edition.get("title", ""),
        series=series,
        series_index=index,
        isbn=isbn,
        publisher=(edition.get("publishers") or [""])[0],
        date=_date(edition.get("publish_date", "")),
        description=description.strip(),
        language=languages[0].get("key", "").rsplit("/", 1)[-1],
    )


def fill(book: Metadata, found: Metadata) -> tuple[Metadata, dict[str, str]]:
    """Merge a lookup into what the book says of itself.

    Returns the merged metadata, where each field is the book's own value when it
    has one and found's otherwise, and a map from each field that ended up with a
    value to its source, "book" or "Open Library". A field empty in both is left
    empty and absent from the map.
    """
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
    """Open Library's free-text date as W3CDTF, at the precision it gives.

    A string, not a date: "2021" or "September 2021" has no day to put in one,
    and the OPF this is written into holds the date as text. Text that matches
    no known form, such as "circa 1900", is kept as it is.
    """
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
