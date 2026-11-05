import json
import re
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from bookdrop.metadata import Metadata

ID = re.compile(r"[0-9a-f]{32}")


@dataclass
class Drop:
    """One upload awaiting confirmation, kept in its own directory under /data."""

    directory: Path
    uploaded_as: str = ""
    # How the upload became a DRM-free book; see adept.Prepared.
    preparation: str = ""
    book_name: str = ""
    metadata: Metadata = field(default_factory=Metadata)
    # Where each field's value came from: "book", "Open Library", "alias", "you".
    sources: dict[str, str] = field(default_factory=dict)
    # What the last Open Library lookup came to, said to the person.
    lookup: str = ""
    lookup_failed: bool = False
    confirmed: bool = False
    created: str = ""

    @property
    def id(self) -> str:
        return self.directory.name

    @property
    def book(self) -> Path:
        return self.directory / self.book_name

    @property
    def extension(self) -> str:
        return self.book.suffix.lstrip(".")

    def save(self) -> None:
        record = asdict(self)
        # The directory is where the record lives, not part of it.
        del record["directory"]
        # Written beside and renamed over, which is atomic: a restart mid-write
        # leaves the old record or the new, never a truncated one that every
        # page listing the drops would fail to parse.
        tmp = self.directory / "drop.json.tmp"
        tmp.write_text(json.dumps(record, indent=2))
        tmp.replace(self.directory / "drop.json")


def root(data_dir: Path) -> Path:
    return data_dir / "drops"


def new_directory(data_dir: Path) -> Path:
    directory = root(data_dir) / uuid.uuid4().hex
    directory.mkdir(parents=True)
    return directory


def discard(directory: Path) -> None:
    shutil.rmtree(directory)


def load(data_dir: Path, drop_id: str) -> Drop | None:
    if not ID.fullmatch(drop_id):
        return None
    directory = root(data_dir) / drop_id
    try:
        record = json.loads((directory / "drop.json").read_text())
    except FileNotFoundError:
        return None
    record["metadata"] = Metadata.from_dict(record["metadata"])
    return Drop(directory=directory, **record)


def all_drops(data_dir: Path) -> list[Drop]:
    """Every saved drop, newest first. A directory without drop.json is skipped."""
    if not root(data_dir).exists():
        return []
    found = (load(data_dir, d.name) for d in root(data_dir).iterdir() if d.is_dir())
    return sorted((d for d in found if d), key=lambda d: d.created, reverse=True)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
