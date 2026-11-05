import re
import tomllib
import unicodedata
from pathlib import Path, PurePosixPath

from bookdrop.metadata import Metadata

# Paths are ASCII. The share's Samba fails any character above U+00FF with EIO
# and stores the rest as Latin-1, while the library's older accented names are
# UTF-8 on disk and read through SMB as mojibake ("MiÃ©ville"). ASCII bytes are
# the same in every one of those encodings, and stay so when the share moves to
# UTF-8. The true text stays in the metadata.
FOLDS = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u02bc": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2026": "...",
        "\u00a0": " ",
        # Letters Unicode does not decompose into an ASCII base.
        "\u00df": "ss",
        "\u00c6": "AE",
        "\u00e6": "ae",
        "\u00d8": "O",
        "\u00f8": "o",
        "\u00de": "Th",
        "\u00fe": "th",
        "\u00d0": "D",
        "\u00f0": "d",
        "\u0141": "L",
        "\u0142": "l",
        "\u0110": "D",
        "\u0111": "d",
        "\u0152": "OE",
        "\u0153": "oe",
    }
)
# Not allowed in a Windows or SMB filename; Calibre writes these as "_".
RESERVED = re.compile(r'[\\/*?"<>|]')


def fold(text: str) -> str:
    """One path component, spelt so the share can store it."""
    text = text.translate(FOLDS)
    # The library writes "Chapterhouse: Dune" as "Chapterhouse - Dune".
    text = re.sub(r"\s*:\s*", " - ", text)
    text = RESERVED.sub("_", text)
    out = []
    for char in text:
        if char.isascii():
            out.append(char)
            continue
        base = "".join(
            c
            for c in unicodedata.normalize("NFKD", char)
            if not unicodedata.combining(c)
        )
        out.append(base if base and base.isascii() else "_")
    # Windows and Samba drop a trailing dot or space, so a name ending in one
    # would not round-trip.
    return " ".join("".join(out).split()).rstrip(". ") or "_"


def aliases(path: Path) -> dict[str, str]:
    """[aliases] from the TOML file at path; empty when it does not exist."""
    if not path.exists():
        return {}
    with path.open("rb") as f:
        table = tomllib.load(f).get("aliases", {})
    return {str(k): str(v) for k, v in table.items()}


def canonical(authors: list[str], table: dict[str, str]) -> list[str]:
    return [table.get(a, a) for a in authors]


def destination(meta: Metadata, extension: str) -> PurePosixPath:
    """Where the book goes under the books root: Author/[Series/]Title/Title.ext."""
    # Calibre's own joining, as the library's sidecars come from Calibre.
    author = fold(" & ".join(meta.authors) or "Unknown")
    title = fold(meta.title or "Untitled")
    parts = [author]
    if meta.series:
        parts.append(fold(meta.series))
    parts.append(title)
    return PurePosixPath(*parts, f"{title}.{extension}")
