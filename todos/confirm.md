# confirm: the upload page and the confirmation screen

## Opening prompt

> Read `todos/confirm.md` and *Metadata* and *Layout* in `docs/design.md`. Turn
> the bare upload form into the page a phone uses, and add the confirmation
> screen: metadata read from the book, gaps filled by ISBN lookup, every field
> editable, and the destination path shown before anything is filed.

## The work

- An upload page that works one-handed on a phone: one file picker, accepting
  `.acsm` and `.epub`, progress while fulfilment runs.
- Read title, author, series, index, ISBN, publisher, date, description,
  language and cover from the OPF. Calibre writes series as
  `calibre:series` and `calibre:series_index` meta elements; EPUB 3 uses
  `belongs-to-collection`. Read both.
- Fill gaps by ISBN from Open Library, then Google Books, keyless. Lookup
  failure is not an error: the screen shows what is known.
- The author alias table: a TOML file in `/data`, editable without a release.
- The screen shows the computed destination, Latin-1 folded, and says when it
  already exists.
- Uploads awaiting confirmation live under `/data` and survive a restart.

## What a Kobo EPUB carries

Measured on the first purchase, 2026-11-03: an EPUB 3 OPF with title, one
creator, publisher, `en-US` and `dcterms:date` as a bare year. No ISBN in
`dc:identifier`, which is a UUID; the print ISBN is in
`dc:source` (`urn:isbn:…`) with an ONIX identifier-type refinement, and the
ebook's own ISBN only in the cover image's filename. The book is standalone, so
whether Kobo writes series metadata is still unknown: check the first series
purchase. The cover is a manifest item named by the `cover` meta.

The lookup should try `dc:source`'s ISBN when `dc:identifier` has none.

## Done when

On a phone, a fresh purchase reaches the confirmation screen with title and
author correct, and an edit to the series changes the destination shown.
