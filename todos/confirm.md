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

## Not yet checked

What metadata a Kobo EPUB actually carries, series in particular. Check it
against the first Kobo purchase (see `adept.md`) before deciding how much the lookup has to supply.

## Done when

On a phone, a fresh purchase reaches the confirmation screen with title and
author correct, and an edit to the series changes the destination shown.
