# confirm: the upload page and the confirmation screen

## Opening prompt

> Read `todos/confirm.md` and *Metadata* and *Layout* in `docs/design.md`. Turn
> the bare upload form into the page a phone uses, and add the confirmation
> screen: metadata read from the book, gaps filled by ISBN lookup, every field
> editable, and the destination path shown before anything is filed.

## Where it stands

Built on the `confirm` branch, 2026-11-03. A drop now leads to its confirmation
page: metadata read from the book, gaps filled from Open Library, every field
editable with where its value came from, the cover, the destination and a
warning when it exists. Drops live under `/data/drops/` and are listed on the
upload page. Confirming records the decision and files nothing; `filing` builds
the writer.

Measured in the image the same day: the first purchase's `.acsm` reached its
confirmation page in 3.8 s, fulfilment and lookup included, with every field
right and the description from Open Library; an edit to the series moved the
destination. The design's *Metadata* and *Layout* hold what is now true.

## What a Kobo EPUB carries

Measured on the first purchase, 2026-11-03: an EPUB 3 OPF with title, one
creator, publisher, `en-US` and `dcterms:date` as a bare year. No ISBN in
`dc:identifier`, which is a UUID; the print ISBN is in
`dc:source` (`urn:isbn:…`) with an ONIX identifier-type refinement, and the
ebook's own ISBN only in the cover image's filename. The book is standalone, so
whether Kobo writes series metadata is still unknown: check the first series
purchase. The cover is a manifest item named by the `cover` meta.

## Done when

On a phone, a fresh purchase reaches the confirmation screen with title and
author correct, and an edit to the series changes the destination shown.
