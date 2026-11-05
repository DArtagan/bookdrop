import re

import pytest
from conftest import ACSM, drm_epub, make_epub
from fastapi.testclient import TestClient

from bookdrop.config import Settings
from bookdrop.lookup import LookupFailed
from bookdrop.metadata import Metadata
from bookdrop.web import create_app

JPEG = b"\xff\xd8\xff\xe0 not really a jpeg"
BOOK = """
<dc:title>Dune Messiah</dc:title>
<dc:creator>Frank Herbert</dc:creator>
<dc:identifier opf:scheme="ISBN">9780441015610</dc:identifier>
<meta name="cover" content="c"/>
"""


@pytest.fixture
def settings(tmp_path):
    (tmp_path / "books").mkdir()
    return Settings(
        data_dir=tmp_path / "data",
        books_root=tmp_path / "books",
        adept_dir=tmp_path / "adept",
    )


@pytest.fixture
def looked_up():
    """The ISBNs the app looked up, and what each answers: Metadata, None for
    no record, or a LookupFailed to raise."""
    return {"asked": [], "answers": {}}


@pytest.fixture
def client(settings, looked_up):
    def find(isbn: str) -> Metadata | None:
        looked_up["asked"].append(isbn)
        answer = looked_up["answers"].get(isbn)
        if isinstance(answer, LookupFailed):
            raise answer
        return answer

    return TestClient(create_app(settings, find=find))


def drop(client, tmp_path, **epub) -> str:
    book = make_epub(tmp_path / "upload.epub", **epub).read_bytes()
    response = client.post(
        "/drop", files={"file": ("upload.epub", book)}, follow_redirects=False
    )
    assert response.status_code == 303
    return response.headers["location"]


def form(page: str) -> dict[str, str]:
    """The confirmation form's fields as the page shows them."""
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', page))
    fields.update(re.findall(r'name="(\w+)">([^<]*)</textarea>', page))
    return fields


def test_dry_run_unless_disabled(monkeypatch):
    monkeypatch.delenv("BOOKDROP_DRY_RUN", raising=False)
    assert Settings().dry_run is True


def test_dry_run_disabled_explicitly(monkeypatch):
    monkeypatch.setenv("BOOKDROP_DRY_RUN", "false")
    assert Settings().dry_run is False


def test_healthz_reports_mode(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "dry_run": True}


def test_index_states_dry_run(client):
    assert "nothing in the library is changed" in client.get("/").text


def test_file_picker_filters_nothing(client):
    # iOS refuses .acsm files from a picker that names accepted types.
    assert "accept=" not in client.get("/").text


def test_drop_leads_to_its_confirmation(client, tmp_path):
    page = client.get(drop(client, tmp_path, metadata=BOOK, version="2.0")).text
    assert "<h1>Dune Messiah</h1>" in page
    assert "It arrived DRM-free." in page
    assert form(page)["authors"] == "Frank Herbert"
    assert "<code>Frank Herbert/Dune Messiah/Dune Messiah.epub</code>" in page


def test_an_edit_to_the_series_changes_the_destination(client, tmp_path):
    location = drop(client, tmp_path, metadata=BOOK, version="2.0")
    fields = form(client.get(location).text) | {"series": "Dune", "series_index": "2"}

    page = client.post(location, data=fields | {"action": "update"}).text

    assert "<code>Frank Herbert/Dune/Dune Messiah/Dune Messiah.epub</code>" in page
    assert "from you" in page
    assert "Confirmed." not in page


def test_confirm_is_recorded_and_files_nothing(client, settings, tmp_path):
    location = drop(client, tmp_path, metadata=BOOK, version="2.0")
    fields = form(client.get(location).text)

    page = client.post(location, data=fields | {"action": "confirm"}).text

    assert "Confirmed." in page
    assert list(settings.books_root.iterdir()) == []
    assert "Confirmed · dropped" in client.get("/").text


def test_lookup_fills_only_the_gaps(client, tmp_path, looked_up):
    looked_up["answers"]["9780441015610"] = Metadata(
        title="Another Title", publisher="Ace", description="A sequel."
    )
    page = client.get(drop(client, tmp_path, metadata=BOOK, version="2.0")).text
    fields = form(page)
    assert looked_up["asked"] == ["9780441015610"]
    assert fields["title"] == "Dune Messiah"
    assert fields["publisher"] == "Ace"
    assert fields["description"] == "A sequel."
    assert "from Open Library" in page


def test_no_isbn_no_lookup(client, tmp_path, looked_up):
    drop(client, tmp_path)
    assert looked_up["asked"] == []


def test_an_existing_path_is_flagged(client, settings, tmp_path):
    (settings.books_root / "Frank Herbert" / "Dune Messiah").mkdir(parents=True)
    page = client.get(drop(client, tmp_path, metadata=BOOK, version="2.0")).text
    assert "already at this path" in page


def test_aliases_apply_to_the_proposal_and_to_edits(client, settings, tmp_path):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "authors.toml").write_text(
        '[aliases]\n"F. Herbert" = "Frank Herbert"\n'
    )
    location = drop(
        client,
        tmp_path,
        metadata="<dc:title>T</dc:title><dc:creator>F. Herbert</dc:creator>",
    )
    page = client.get(location).text
    assert form(page)["authors"] == "Frank Herbert"
    assert "from alias" in page

    page = client.post(
        location, data=form(page) | {"authors": "F. Herbert", "action": "update"}
    ).text
    assert form(page)["authors"] == "Frank Herbert"


def test_unreadable_aliases_are_reported(client, settings, tmp_path):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "authors.toml").write_text("[aliases\n")
    page = client.get(drop(client, tmp_path)).text
    assert "authors.toml could not be read" in page


def test_cover(client, tmp_path):
    location = drop(
        client,
        tmp_path,
        metadata=BOOK,
        manifest="<item id='c' href='c.jpg' media-type='image/jpeg'/>",
        files={"OEBPS/c.jpg": JPEG},
        version="2.0",
    )
    response = client.get(f"{location}/cover")
    assert response.content == JPEG
    assert response.headers["content-type"] == "image/jpeg"


def test_drops_survive_a_restart(settings, tmp_path):
    first = TestClient(create_app(settings, find=lambda isbn: None))
    location = drop(first, tmp_path, metadata=BOOK, version="2.0")
    second = TestClient(create_app(settings, find=lambda isbn: None))
    assert "Dune Messiah" in second.get("/").text
    assert "<h1>Dune Messiah</h1>" in second.get(location).text


@pytest.mark.parametrize("drop_id", ["../../etc", "0" * 32, "nonsense"])
def test_unknown_drop(client, drop_id):
    assert client.get(f"/drops/{drop_id}").status_code == 404


def test_refused_drop_keeps_nothing(client, settings):
    response = client.post("/drop", files={"file": ("notes.txt", b"plain text")})
    assert response.status_code == 422
    assert "Only an .acsm, an EPUB or a PDF" in response.text
    assert list((settings.data_dir / "drops").iterdir()) == []


def test_drop_of_an_acsm(client, settings, tmp_path, tools, adept_dir, monkeypatch):
    monkeypatch.setenv("STUB_FULFILLED", str(drm_epub(tmp_path / "drm.epub")))
    monkeypatch.setenv(
        "STUB_STRIPPED", str(make_epub(tmp_path / "clean.epub", title="Real Title"))
    )
    app = create_app(
        Settings(
            data_dir=settings.data_dir,
            books_root=settings.books_root,
            adept_dir=adept_dir,
        ),
        find=lambda isbn: None,
    )
    response = TestClient(app).post("/drop", files={"file": ("URLLink.acsm", ACSM)})
    assert "<h1>Real Title</h1>" in response.text
    assert "Downloaded from the store, DRM removed." in response.text


@pytest.mark.parametrize(
    ("series", "index", "problem"),
    [
        ("Dune", "two", "must be a number"),
        ("Dune", "NaN", "must be a number"),
        ("Dune", "-1", "must be a number"),
        ("", "2", "needs a series"),
    ],
)
def test_confirm_refuses_an_unfileable_series(client, tmp_path, series, index, problem):
    location = drop(client, tmp_path, metadata=BOOK, version="2.0")
    fields = form(client.get(location).text) | {
        "series": series,
        "series_index": index,
    }

    page = client.post(location, data=fields | {"action": "confirm"}).text

    assert "Not confirmed: " in page and problem in page
    assert "Confirmed." not in page


def test_confirm_takes_a_fractional_series_number(client, tmp_path):
    location = drop(client, tmp_path, metadata=BOOK, version="2.0")
    fields = form(client.get(location).text) | {"series": "Dune", "series_index": "3.5"}
    page = client.post(location, data=fields | {"action": "confirm"}).text
    assert "Confirmed." in page


def test_genres_are_edited_one_a_line(client, tmp_path):
    location = drop(
        client,
        tmp_path,
        metadata=BOOK + "<dc:subject>Fantasy</dc:subject>",
        version="2.0",
    )
    fields = form(client.get(location).text)
    assert fields["genres"] == "Fantasy"

    page = client.post(
        location,
        data=fields
        | {"genres": "Fantasy\r\nFiction, fantasy, epic\r\n\r\n", "action": "update"},
    ).text

    assert form(page)["genres"] == "Fantasy\nFiction, fantasy, epic"
    assert "Genres, one a line <small>from you" in page


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"title": ""}, "needs a title"),
        ({"authors": " & "}, "needs at least one author"),
        ({"isbn": "9780441015611"}, "check digit is wrong"),
    ],
)
def test_confirm_refuses_a_book_it_cannot_file(client, tmp_path, change, problem):
    location = drop(client, tmp_path, metadata=BOOK, version="2.0")
    fields = form(client.get(location).text) | change

    page = client.post(location, data=fields | {"action": "confirm"}).text

    assert problem in page
    assert "Confirmed." not in page


def test_a_book_without_a_title_is_not_named_after_its_upload(client, tmp_path):
    page = client.get(drop(client, tmp_path, title=None)).text
    assert form(page)["title"] == ""
    assert "<h1>Untitled</h1>" in page


def test_lookup_says_what_it_filled(client, tmp_path, looked_up):
    looked_up["answers"]["9780441015610"] = Metadata(publisher="Ace", date="1969")
    page = client.get(drop(client, tmp_path, metadata=BOOK, version="2.0")).text
    assert "Open Library filled 2 fields." in page


def test_no_record_is_said(client, tmp_path):
    page = client.get(drop(client, tmp_path, metadata=BOOK, version="2.0")).text
    assert "Open Library has no record of ISBN 9780441015610." in page


def test_no_isbn_is_said(client, tmp_path):
    page = client.get(drop(client, tmp_path)).text
    assert "No ISBN, so Open Library was not asked." in page
    assert "Look up again" not in page


def test_a_failed_lookup_is_shown_logged_and_can_be_retried(
    client, tmp_path, looked_up, caplog
):
    looked_up["answers"]["9780441015610"] = LookupFailed("ConnectTimeout: timed out")
    location = drop(client, tmp_path, metadata=BOOK, version="2.0")
    page = client.get(location).text

    assert "could not be asked about 9780441015610: ConnectTimeout: timed out" in page
    assert 'class="warn">Open Library could not be asked' in page
    assert "Look up again" in page
    assert "Open Library lookup of 9780441015610 failed" in caplog.text

    looked_up["answers"]["9780441015610"] = Metadata(publisher="Ace")
    fields = form(page) | {"title": "Edited Title"}
    page = client.post(location, data=fields | {"action": "lookup"}).text

    assert "Open Library filled 1 field." in page
    assert 'class="warn"' not in page
    assert form(page)["publisher"] == "Ace"
    assert form(page)["title"] == "Edited Title"
    assert "Title <small>from you" in page


def test_look_up_again_uses_a_corrected_isbn(client, tmp_path, looked_up):
    looked_up["answers"]["9780765376671"] = Metadata(publisher="Tor")
    location = drop(client, tmp_path, metadata=BOOK, version="2.0")
    fields = form(client.get(location).text) | {"isbn": "9780765376671"}
    page = client.post(location, data=fields | {"action": "lookup"}).text
    assert looked_up["asked"] == ["9780441015610", "9780765376671"]
    assert form(page)["publisher"] == "Tor"
