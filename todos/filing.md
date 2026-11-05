# filing: the book written into the library, and Stump scanning

## Opening prompt

> Read `todos/filing.md` and *Layout* and *Rules that protect the library* in
> `docs/design.md`. Build the executor, the one writer under the books root,
> and file confirmed books for real.

## What Stump reads

Read from Stump's source at its deployed tag, v0.1.11
(`core/src/media/processor/epub.rs`, `core/src/metadata/media.rs`), and its
database, on 2026-11-05. Writing the OPF has to meet this, not the EPUB
standard alone:

- **Series only as Calibre writes it**: `<meta name="calibre:series">` and
  `calibre:series_index`. EPUB 3's `belongs-to-collection` and
  `group-position` are ignored. Write the Calibre pair.
- **ISBN only as `<dc:identifier opf:scheme="ISBN">`.** An EPUB 3 identifier
  typed by refinement, and `dc:source`, are ignored, so the first Kobo book's
  ISBN never reached Stump. Write it with `opf:scheme`.
- **`dc:subject` becomes Stump's genres**, and Calibre's tags are written as
  `dc:subject`: 85 of the library's 259 books have genres this way.
- **`calibre:title_sort`** is read for sorting; 225 books have it. Derive it
  ("The Way of Kings" to "Way of Kings, The") rather than ask for it.
- Every `dc:creator` becomes a writer, whatever its role. `dc:description`
  is the summary. `dc:date` is parsed in any of the forms `confirm` produces.
- **A sidecar is read only as `<book>.opf`**, beside `<book>.epub`, and it
  overrides the EPUB's own metadata. Stump never reads `metadata.opf`, which is
  Calibre's name for the same file and the one the library's books carry.
- **The library is collection-based**: each author folder is one Stump series
  (126 of them). A book's own series in Stump comes only from its embedded
  metadata; the `Series/` folder level organises the share, not Stump.

No EPUB in the library has a year in Stump, though they carry `dc:date` in a
form 0.1.11 parses. The likeliest cause is metadata recorded by an older Stump
and not re-read; it was not confirmed. A book bookdrop files is scanned fresh.

## The work

- The executor: every write under `/books` goes through it, and it refuses
  while dry run is on. A test fails if any other module opens a path under the
  books root for writing.
- Write the confirmed metadata into the EPUB's OPF, in the forms *What Stump
  reads* names, and alongside it write `metadata.opf` and `cover.jpg`.
  `metadata.opf` stays although Stump ignores it (Will, 2026-11-05): it is the
  Calibre-compatible backup every other book in the library carries. Not
  `<book>.opf`, which Stump would read in preference to the EPUB, leaving two
  copies of the metadata to drift. Calibre's `ebook-meta` was the first idea, but
  Calibre is a large dependency for one rewrite of an XML file inside a zip;
  choose deliberately and record why.
- A Stump API key in the deployment's secret, and a scan of the library after
  each filing. The mutation or endpoint that starts a scan was not looked up;
  Stump 0.1.11 is deployed, and its API is GraphQL with some REST routes
  (<https://www.stumpapp.dev/docs/developer/api>).
- Going live: `BOOKDROP_DRY_RUN=false` and a writable books mount, together, in
  the deployment repository.

## Done when

- The book appears in Stump with its title, author and series as confirmed,
  and opens in Stump's reader.
- `ls` of its directory on the share shows the EPUB, `metadata.opf` and
  `cover.jpg`, in the layout of the books beside it.
