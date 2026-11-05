# filing: the book written into the library, and Stump scanning

## Opening prompt

> Read `todos/filing.md` and *Filing* and *Rules that protect the library* in
> `docs/design.md`. The code is built and tested; what remains is the Stump API
> key, the deployment's writable books volume, and the first real book filed.

## Where it stands

Built on the `filing` branch, 2026-11-05: the OPF rewriter (`opf.py`), the
plan of what filing writes (`filing.py`), the executor (`executor.py`) and the
scan (`stump.py`), wired to the confirmation page. *Filing* in the design is
what is now true.

Measured that day, in the image, filing the first Kobo purchase into a scratch
directory: the book, `cover.jpg` and `metadata.opf` landed in
`Author/Series/Title/`; Calibre read title, author, series, ISBN and genres back
from both the EPUB and `metadata.opf`; epubcheck found only the three errors
Kobo's original has. Rewriting *Dune Messiah* from the library, a Calibre EPUB 2,
changed none of its fields and added no epubcheck finding. An unconfigured scan
was shown on the page and logged.

The deployment holds Stump's URL, the library's id and a key with only
`ScanLibrary`, since 2026-11-05. That day, the scan request bookdrop sends, made
from the deployed pod with that key, was accepted, and Stump's job record shows
the library scan completing in 22.8 s.

## What remains

- **A writable books volume.** Nothing could write into the books share on
  2026-11-05, its owner and modes refusing the share's account. The deployment
  repository's move of that share to NFS fixes it; going live waits on that,
  then is `BOOKDROP_DRY_RUN=false` and the volume writable, together.

## Done when

- The book appears in Stump with its title, author and series as confirmed,
  and opens in Stump's reader.
- `ls` of its directory on the share shows the EPUB, `metadata.opf` and
  `cover.jpg`, in the layout of the books beside it.
