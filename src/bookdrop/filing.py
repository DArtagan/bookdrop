import io
from dataclasses import dataclass
from pathlib import PurePosixPath

from PIL import Image

from bookdrop import layout, metadata, opf
from bookdrop.drops import Drop

JPEG_QUALITY = 90


@dataclass(frozen=True)
class Plan:
    """What filing a book writes: a new directory under the books root, and the
    files in it, in the order they are written."""

    directory: PurePosixPath
    files: dict[str, bytes]


def plan(drop: Drop) -> Plan:
    """The files a confirmed drop becomes. Reads the drop; writes nothing."""
    meta = drop.metadata
    destination = layout.destination(meta, drop.extension)
    if drop.extension == "epub":
        book = opf.rewrite(drop.book, meta)
    else:
        book = drop.book.read_bytes()
    files = {destination.name: book}
    image = metadata.cover(drop.book)
    if image is not None:
        files["cover.jpg"] = jpeg(*image)
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
