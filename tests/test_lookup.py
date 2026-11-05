import httpx
import pytest

from bookdrop.lookup import LookupFailed, _date, _series, fill, open_library
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
WORK = {
    "title": "The Right Book",
    "description": {"value": "About the book."},
    "subjects": ["Fantasy", "nyt:hardcover-fiction=2010-09-19"],
}
AUTHOR = {"name": "An Author"}


def client(routes: dict[str, object], asked: list | None = None) -> httpx.Client:
    def handle(request: httpx.Request) -> httpx.Response:
        if asked is not None:
            asked.append(request.url.path)
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
    asked = []
    http = client(
        {
            "/isbn/9780374248529.json": EDITION,
            "/works/OL1W.json": WORK,
            "/authors/OL1A.json": AUTHOR,
        },
        asked,
    )
    found = open_library("9780374248529", http)
    assert asked == ["/isbn/9780374248529.json", "/works/OL1W.json"]
    assert found.title == "The Right Book"
    assert found.authors == []
    assert found.publisher == "A Publisher"
    assert found.date == "2021-09-21"
    assert found.description == "About the book."
    assert found.language == "eng"
    assert found.genres == []


@pytest.mark.parametrize(
    ("failure", "said"),
    [
        (500, "HTTPStatusError"),
        (httpx.ConnectTimeout("timed out"), "ConnectTimeout: timed out"),
        (httpx.ConnectError("unreachable"), "ConnectError: unreachable"),
        (["not", "an", "edition"], "could not read"),
    ],
)
def test_a_failure_is_raised_not_mistaken_for_no_record(failure, said):
    http = client({"/isbn/1.json": failure})
    with pytest.raises(LookupFailed, match=said):
        open_library("1", http)


def test_a_failure_fetching_the_work_is_raised_too():
    http = client({"/isbn/1.json": EDITION, "/works/OL1W.json": 503})
    with pytest.raises(LookupFailed):
        open_library("1", http)


def test_unknown_isbn_is_no_record():
    assert open_library("1", client({})) is None


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


def test_fill_keeps_each_values_source():
    current = Metadata(title="Typed", publisher="Theirs")
    found = Metadata(title="Other", publisher="X", date="2021")
    merged, sources = fill(
        current, found, {"title": "you", "publisher": "Open Library"}
    )
    assert (merged.title, merged.publisher, merged.date) == ("Typed", "Theirs", "2021")
    assert sources == {
        "title": "you",
        "publisher": "Open Library",
        "date": "Open Library",
    }


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


def test_user_agent_names_bookdrop():
    from bookdrop.lookup import client as lookup_client

    with lookup_client() as http:
        agent = http.headers["User-Agent"]
    assert agent.startswith("bookdrop/")
    assert agent.endswith("(+https://github.com/DArtagan/bookdrop)")
