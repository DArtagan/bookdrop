import httpx
import pytest

from bookdrop.lookup import _date, _series, fill, open_library
from bookdrop.metadata import Metadata

# Shaped as Open Library answered for the first Kobo purchase on 2026-11-03.
EDITION = {
    "title": "The Right Book",
    "publishers": ["A Publisher"],
    "publish_date": "Sep 21, 2021",
    "authors": [{"key": "/authors/OL1A"}],
    "languages": [{"key": "/languages/eng"}],
    "works": [{"key": "/works/OL1W"}],
}
WORK = {"title": "The Right Book", "description": {"value": "About the book."}}
AUTHOR = {"name": "An Author"}


def client(routes: dict[str, object]) -> httpx.Client:
    def handle(request: httpx.Request) -> httpx.Response:
        answer = routes.get(request.url.path)
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            return httpx.Response(404)
        if isinstance(answer, int):
            return httpx.Response(answer)
        return httpx.Response(200, json=answer)

    return httpx.Client(
        base_url="https://openlibrary.org", transport=httpx.MockTransport(handle)
    )


def test_open_library_record():
    http = client(
        {
            "/isbn/9780374248529.json": EDITION,
            "/works/OL1W.json": WORK,
            "/authors/OL1A.json": AUTHOR,
        }
    )
    found = open_library("9780374248529", http)
    assert found.title == "The Right Book"
    assert found.authors == ["An Author"]
    assert found.publisher == "A Publisher"
    assert found.date == "2021-09-21"
    assert found.description == "About the book."
    assert found.language == "eng"


def test_authors_from_the_work_when_the_edition_has_none():
    edition = {**EDITION, "authors": []}
    work = {**WORK, "authors": [{"author": {"key": "/authors/OL1A"}}]}
    http = client(
        {
            "/isbn/1.json": edition,
            "/works/OL1W.json": work,
            "/authors/OL1A.json": AUTHOR,
        }
    )
    assert open_library("1", http).authors == ["An Author"]


@pytest.mark.parametrize(
    "failure",
    [500, httpx.ConnectTimeout("slow"), httpx.ConnectError("unreachable")],
)
def test_failure_is_an_empty_answer(failure):
    http = client({"/isbn/1.json": failure})
    assert open_library("1", http) == Metadata()


def test_unknown_isbn_is_an_empty_answer():
    assert open_library("1", client({})) == Metadata()


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ("The Stormlight Archive ; bk. 1", ("The Stormlight Archive", "1")),
        ("Dune (2)", ("Dune", "2")),
        ("Discworld, #4", ("Discworld", "4")),
        ("Wayfarers -- 3.5", ("Wayfarers", "3.5")),
        ("Penguin Classics", ("Penguin Classics", "")),
    ],
)
def test_series(entry, expected):
    assert _series([entry]) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Sep 21, 2021", "2021-09-21"),
        ("September 2021", "2021-09"),
        ("2021", "2021"),
        ("circa 1900", "circa 1900"),
    ],
)
def test_date(text, expected):
    assert _date(text) == expected


def test_fill_keeps_the_books_own_values():
    book = Metadata(title="Own Title", authors=["Own Author"])
    found = Metadata(title="Their Title", authors=["X"], publisher="Their Press")
    merged, sources = fill(book, found)
    assert merged.title == "Own Title"
    assert merged.authors == ["Own Author"]
    assert merged.publisher == "Their Press"
    assert sources == {
        "title": "book",
        "authors": "book",
        "publisher": "Open Library",
    }
