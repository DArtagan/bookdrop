# filing: the book written into the library, and Stump scanning

## Opening prompt

> Read `todos/filing.md` and *Layout* and *Rules that protect the library* in
> `docs/design.md`. Build the executor, the one writer under the books root,
> and file confirmed books for real.

## The work

- The executor: every write under `/books` goes through it, and it refuses
  while dry run is on. A test fails if any other module opens a path under the
  books root for writing.
- Write the confirmed metadata into the EPUB's OPF, and alongside it write
  `metadata.opf` and `cover.jpg`. Calibre's `ebook-meta` was the first idea, but
  Calibre is a large dependency for one rewrite of an XML file inside a zip;
  choose deliberately and record why.
- Latin-1 folding for every path component, with a test for each character
  the design names.
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
