import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

DC = "{http://purl.org/dc/elements/1.1/}"


def title(book: Path) -> str | None:
    """The EPUB's own title, or None when it has none or is not an EPUB."""
    try:
        with zipfile.ZipFile(book) as z:
            container = ET.fromstring(z.read("META-INF/container.xml"))
            rootfile = next(
                e for e in container.iter() if e.tag.rsplit("}", 1)[-1] == "rootfile"
            )
            opf = ET.fromstring(z.read(rootfile.get("full-path", "")))
    except zipfile.BadZipFile, KeyError, StopIteration, ET.ParseError:
        return None
    element = opf.find(f".//{DC}title")
    text = (element.text or "").strip() if element is not None else ""
    return text or None
