from pathlib import PurePosixPath

import pytest

from bookdrop.executor import DryRun, Executor, Exists
from bookdrop.filing import Plan

PLAN = Plan(
    PurePosixPath("Author/Series/Title"),
    {"Title.epub": b"book", "cover.jpg": b"jpeg", "metadata.opf": b"opf"},
)


def tree(root) -> set[str]:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


def test_dry_run_writes_nothing(tmp_path):
    with pytest.raises(DryRun):
        Executor(tmp_path, dry_run=True).file(PLAN)
    assert tree(tmp_path) == set()


def test_files_the_plan(tmp_path):
    target = Executor(tmp_path, dry_run=False).file(PLAN)
    assert target == tmp_path / "Author/Series/Title"
    assert (target / "Title.epub").read_bytes() == b"book"
    assert tree(tmp_path) == {
        "Author",
        "Author/Series",
        "Author/Series/Title",
        "Author/Series/Title/Title.epub",
        "Author/Series/Title/cover.jpg",
        "Author/Series/Title/metadata.opf",
    }


def test_never_writes_over_an_existing_book(tmp_path):
    existing = tmp_path / "Author/Series/Title"
    existing.mkdir(parents=True)
    (existing / "Title.epub").write_bytes(b"theirs")
    with pytest.raises(Exists):
        Executor(tmp_path, dry_run=False).file(PLAN)
    assert (existing / "Title.epub").read_bytes() == b"theirs"
    assert tree(existing) == {"Title.epub"}


def test_a_failure_leaves_nothing_it_made(tmp_path):
    (tmp_path / "Author").mkdir()
    (tmp_path / "Author/Other Book").mkdir()
    broken = Plan(
        PurePosixPath("Author/Series/Title"),
        {"Title.epub": b"book", "missing/cover.jpg": b"jpeg"},
    )
    with pytest.raises(FileNotFoundError):
        Executor(tmp_path, dry_run=False).file(broken)
    assert tree(tmp_path) == {"Author", "Author/Other Book"}
