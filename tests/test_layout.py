import tomllib
from pathlib import PurePosixPath

import pytest

from bookdrop.layout import AliasesUnreadable, aliases, canonical, destination, fold
from bookdrop.metadata import Metadata


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Earth’s Past", "Earth's Past"),
        ("1995–2002", "1995-2002"),
        # A trailing dot does not survive Windows or SMB clients.
        ("Wait…", "Wait"),
        ("“Quoted”", "_Quoted_"),
        ("Chapterhouse: Dune", "Chapterhouse - Dune"),
        ("Either/Or", "Either_Or"),
        ("Why?", "Why_"),
        ("Café Society", "Cafe Society"),
        ("China Miéville", "China Mieville"),
        ("Marie Kondō", "Marie Kondo"),
        ("Straße", "Strasse"),
        ("Bjørn Ærø", "Bjorn AEro"),
        ("Łódź", "Lodz"),
        ("三体", "__"),
        ("The End.", "The End"),
        ("..", "_"),
        ("  spaced   out  ", "spaced out"),
    ],
)
def test_fold(text, expected):
    folded = fold(text)
    assert folded == expected
    assert folded.isascii()


def test_destination_in_a_series():
    meta = Metadata(title="Dune Messiah", authors=["Frank Herbert"], series="Dune")
    assert destination(meta, "epub") == PurePosixPath(
        "Frank Herbert/Dune/Dune Messiah/Dune Messiah.epub"
    )


def test_destination_standalone_with_several_authors():
    meta = Metadata(title="Zombies vs. Unicorns", authors=["Holly Black", "J. L."])
    assert destination(meta, "pdf") == PurePosixPath(
        "Holly Black & J. L/Zombies vs. Unicorns/Zombies vs. Unicorns.pdf"
    )


def test_destination_without_author_or_title():
    assert destination(Metadata(), "epub") == PurePosixPath(
        "Unknown/Untitled/Untitled.epub"
    )


def test_aliases(tmp_path):
    path = tmp_path / "authors.toml"
    assert aliases(path) == {}
    path.write_text('[aliases]\n"T.A. Pratt" = "Tim Pratt"\n')
    table = aliases(path)
    assert canonical(["T.A. Pratt", "Other"], table) == ["Tim Pratt", "Other"]


@pytest.mark.parametrize(
    ("content", "said"),
    [("[aliases\n", "could not be read"), ('aliases = "x"\n', "is not a table")],
)
def test_unusable_aliases_raise_saying_why(tmp_path, content, said):
    path = tmp_path / "authors.toml"
    path.write_text(content)
    with pytest.raises(AliasesUnreadable, match=said) as raised:
        aliases(path)
    if said == "could not be read":
        assert isinstance(raised.value.__cause__, tomllib.TOMLDecodeError)
