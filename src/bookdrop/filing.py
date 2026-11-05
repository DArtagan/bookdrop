import io
import zipfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath

from lxml import etree
from PIL import Image

from bookdrop import layout, metadata, opf
from bookdrop.drops import Drop
from bookdrop.metadata import Metadata, normalise_isbn

JPEG_QUALITY = 90


class FilingError(Exception):
    """A book could not be filed, with the reason a person reads."""


@dataclass(frozen=True)
class Plan:
    """What filing a book writes: a new directory under the books root, and the
    files in it, in the order they are written."""

    directory: PurePosixPath
    files: dict[str, bytes]


def check(meta: Metadata) -> None:
    """Raises FilingError saying what stops the book being filed as it stands."""
    if not meta.title:
        raise FilingError("A book needs a title.")
    if not meta.authors:
        raise FilingError("A book needs at least one author.")
    if meta.isbn and not normalise_isbn(meta.isbn):
        raise FilingError("The ISBN's check digit is wrong; correct it or clear it.")
    if meta.series_index and not meta.series:
        raise FilingError("A series number needs a series.")
    if meta.series_index:
        try:
            number = Decimal(meta.series_index)
        except InvalidOperation:
            number = None
        # Decimal also reads "NaN" and "Infinity".
        if number is None or not number.is_finite() or number < 0:
            raise FilingError("The series number must be a number, such as 2 or 3.5.")


def plan(drop: Drop) -> Plan:
    """The files a confirmed drop becomes. Reads the drop; writes nothing.

    Raises FilingError when the metadata cannot be filed as it stands (see
    check), or for a book it cannot read: its zip, its OPF or its cover.
    """
    meta = drop.metadata
    check(meta)
    destination = layout.destination(meta, drop.extension)
    try:
        if drop.extension == "epub":
            book = opf.rewrite(drop.book, meta)
        else:
            book = drop.book.read_bytes()
        files = {destination.name: book}
        image = metadata.cover(drop.book)
        if image is not None:
            files["cover.jpg"] = jpeg(*image)
    except (
        etree.LxmlError,
        zipfile.BadZipFile,
        KeyError,
        ValueError,
        OSError,
        metadata.Unreadable,
    ) as error:
        raise FilingError(
            f"The book could not be prepared for filing: {error}"
        ) from error
    files["metadata.opf"] = opf.sidecar(meta, cover=image is not None)
    return Plan(destination.parent, files)


def jpeg(data: bytes, media_type: str) -> bytes:
    """The cover as JPEG: every book in the library has a cover.jpg."""
    if media_type == "image/jpeg":
        return data
    with Image.open(io.BytesIO(data)) as image:
        out = io.BytesIO()
        image.convert("RGB").save(out, "JPEG", quality=JPEG_QUALITY)
        return out.getvalue()
