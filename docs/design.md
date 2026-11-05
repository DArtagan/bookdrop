# Design

bookdrop takes a purchased ebook from a phone or a desktop browser and files it
into the library [Stump](https://www.stumpapp.dev/) reads, with metadata a
person has confirmed. It is the one way books enter that library, so every book
arrives with the same layout, the same sidecars and no DRM.

## The flow

1. Buy the book. From Kobo, choose the Adobe DRM edition.
2. Download what the store offers: an `.acsm` for Adobe DRM, or an EPUB when
   the book is DRM-free.
3. Open bookdrop and upload it. On a phone that is the browser's file picker over
   Downloads; a Web Share Target lets the share sheet send it directly.
4. bookdrop fulfils an `.acsm` into the book, strips the Adobe DRM, reads the
   metadata, and shows it prefilled with the destination path.
5. Accept, or edit and accept. bookdrop files the book and asks Stump to scan.

## Decisions

Made by Will on 2026-11-03, recorded so they are not relitigated:

- **A web drop**, not a share to copy files into, and not a CLI. Kobo's Adobe
  DRM is handled from the start rather than added later.
- **DRM removal is in scope**, for personal backup and reading on any device.
- **Adobe DRM, not Readium LCP.** See *What it does not accept*.
- **A confirmation screen**, not automatic filing. A store's metadata is a
  starting point; series and index in particular are often missing.
- **A dedicated account** for bookdrop's Adobe DRM identity, used by nothing
  else. Will asked for an Adobe ID; see *Adobe identity* for why it is a
  ByteBooks ID.

## Input

| Upload | What happens |
|---|---|
| `.acsm` | `acsmdownloader` fulfils it into an encrypted EPUB or PDF, then `adept_remove` strips the DRM |
| DRM-free `.epub` | straight to metadata |
| anything else | refused, saying why |

A file still encrypted after `adept_remove` is refused: nothing DRM-locked
enters the library. Kobo sells some titles as Adobe PDF; the PDF is kept, and
converting it to EPUB waits until a purchase needs it.

An `.acsm` is not the book but a one-time claim on it. It carries an expiry,
hours after the purchase, and the first Adobe identity to fulfil it owns the
download. bookdrop fulfils one as soon as it arrives. Until it expires, the same
`.acsm` can be fulfilled again against the same device: Kobo's served the book
a second and third time on 2026-11-03. Whether Kobo serves a fresh `.acsm` from
the account's library once one has lapsed was not checked.

### What it does not accept

- **Readium LCP.** Its DRM cannot be removed by any maintained tool: the noDRM
  fork of DeDRM dropped LCP after Readium's
  [2022 DMCA takedown](https://github.com/github/dmca/blob/master/2022/01/2022-01-04-readium.md).
  An LCP book reads only in LCP apps, never in Stump. Some stores offer both;
  choose Adobe.
- **Kindle formats**, until a purchase needs them.

## Adobe identity

[libgourou](https://forge.soutade.fr/soutade/libgourou) implements Adobe's
ADEPT protocol without Adobe Digital Editions: `adept_activate` registers a
device against an Adobe ID, `acsmdownloader` fulfils, `adept_remove` strips.

Adobe handed its ebook platform to Wipro in July 2025, and sign-in for a new
device is now a **ByteBooks ID** (<https://dtsbytebooks.com/register>), not an
Adobe ID. A freshly made Adobe ID fails activation with
`E_AUTH_FAILED … User does not exist`; libgourou's README has said the same
since September 2026.

`adept_activate` runs **once, on a desktop**, against the dedicated ByteBooks
ID. Its output, `device.xml`, `activation.xml` and `devicesalt`, is the device
key.
The deployment holds it as a secret mounted into the container, so:

- the account's password never reaches the server, and
- a restart does not activate a new device. Activations are limited per
  account, and the device key is what the books are fulfilled to.

The device key is backed up with the deployment's secrets. Losing it means
activating again, which spends an activation; books already filed are
unaffected, as they no longer carry DRM.

## Metadata

Read from the book's OPF, EPUB 2 or 3, including Calibre's series. A Kobo EPUB
may carry its ISBN only as `dc:source`, the print edition it was made from, with
`dc:identifier` a UUID; both are read, and an ISBN counts only when its check
digit holds.

With an ISBN, Open Library fills the fields the book leaves empty, never
overriding one it has. It needs no key and answered in two to four seconds on
2026-11-03, so the lookup runs at upload, within a timeout. Its outcome is on the
confirmation screen: what it filled, that Open Library has no record, or that it
could not be asked and why, which is also logged. A failure leaves the book
confirmable, since what the book says of itself is enough to file it, and
*Look up again* retries, with the ISBN as corrected. On 2026-11-05 Open Library
timed out from both the LAN and the cluster. Google Books is not used: without a key it answered
`429 Quota exceeded … Queries per day`, as every keyless caller shares one
quota. A key would make it usable.

Two fields are never filled from Open Library. Authors, because it names each
only by a key costing another request, and EPUBs carry their own. Genres,
because its subjects are not genres: for *The Way of Kings* on 2026-11-05 they
mixed "Fantasy", "Epic Fantasy", "high fantasy" and "Fiction, fantasy, epic"
with "New York Times Bestseller" and `nyt:hardcover-fiction=2010-09-19`, and
each would become a genre in Stump. Genres come from the book's `dc:subject`,
which is where Stump reads them and Calibre writes its tags, or from the person.

The confirmation screen shows each field with where its value came from, the
book, Open Library, the alias table or the person, and every field is editable.
Confirming needs a title and an author, an ISBN only if its check digit holds,
and a series number only as a number beside its series; the screen says which
is missing.
An author alias table, `authors.toml` on the data volume, maps variant spellings
to one canonical name and is read on each request, so it changes without a
release.

## Layout

```
Author/Series/Title/Title.epub     # in a series
Author/Title/Title.epub            # standalone
```

with `cover.jpg` and `metadata.opf` alongside, and the original PDF when that
is what the store sold. This is the layout the library already has: on
2026-11-03 it held 131 author directories and 230 EPUBs, with `metadata.opf`
and `cover.jpg` beside nearly every book, and series one level deeper
(`Frank Herbert/Dune/Dune Messiah/`). A colon in a title is written ` - `
(`Chapterhouse - Dune`).

Several authors are joined with ` & `, as Calibre joins them; the library's
sidecars are Calibre's, and its folders show no convention of their own.

Path components are folded to ASCII (`’` to `'`, `–` to `-`, `é` to `e`,
`ß` to `ss`). The share the library lives on fails any filename character above
U+00FF with `EIO` and stores the rest as Latin-1, while the library's older
accented names are UTF-8 on disk and read through the share as mojibake: on
2026-11-05 Stump saw `China MiÃ©ville` among 96 such paths. ASCII is spelt
the same in all three, and stays so when the share moves to UTF-8. Characters Windows forbids become `_`, and a trailing dot or space is
dropped, as SMB clients cannot round-trip one. The true title stays in the
metadata. A target that already exists is
shown on the confirmation screen, never overwritten.

## Filing

Confirming files the book; in dry run the page lists the files filing would
write instead. A filed book's directory holds:

- **The book**, its OPF rewritten with the confirmed metadata. Only the fields
  bookdrop owns are replaced. The rest of the OPF, rights, accessibility, the
  package's own identifier, other contributors, stays, and so does every other
  entry in the EPUB, byte for byte. A PDF is filed as it came.
- **`metadata.opf`**, the OPF 2.0 sidecar Calibre writes and every other book in
  the library carries. Stump never reads it: it reads a sidecar only when named
  `<book>.opf`, and then in preference to the book itself. bookdrop writes none
  of those, which would leave two copies of the metadata to drift. Kept on Will's
  decision of 2026-11-05.
- **`cover.jpg`**, converted to JPEG when the book's own cover is not.

What Stump reads decides the forms, taken from its source at v0.1.11 on
2026-11-05. It finds a series only as Calibre writes one (`calibre:series`,
`calibre:series_index`), an ISBN only as `<dc:identifier opf:scheme="ISBN">`,
genres in `dc:subject` and the sort title in `calibre:title_sort`, and it matches
tag and attribute names by their literal `dc:` and `opf:` prefixes, so
bookdrop's elements spell those whatever prefixes the book declares. EPUB 3
removed the `opf:` attributes. In an EPUB 3 book bookdrop writes EPUB 3's own
forms, which epubcheck accepts, and Stump then sees no ISBN.

In Stump the library is collection-based: each author's folder is one Stump
series. A book's series shows in Stump only through its metadata, and the
`Series/` level of the layout organises the share, not Stump.

The executor creates the book's directory with `mkdir`, so a second drop bound
for the same place fails rather than writing over the first. Each file is written
beside its name and renamed into place, and a failure removes everything the
filing made. Once filed, a drop keeps its record and lets go of its copy.

After filing, bookdrop asks Stump to scan the whole library, through its GraphQL
API with an API key whose only permission is `ScanLibrary`. Stump's own watcher
never sees a file another client writes to the share, so without the scan a
filed book would not appear. A scan that fails, or is not set up, is shown and
logged; the book stays filed, and a scan started from Stump picks it up.

## Rules that protect the library

- **Dry run is the default.** `BOOKDROP_DRY_RUN` is true unless set to
  `false`. Every write under the library root goes through a single executor
  that checks it, and the deployment mounts the library read-only while dry run
  is on. A test runs every page against a read-only books root with the
  executor replaced, so any other writer there fails it.
- **No real book, `.acsm` or device key enters the repository.** An `.acsm`
  carries a purchase token and the device key is an account credential. Tests
  use synthetic EPUBs, and stand-ins for libgourou's tools.

## Phones

The internal network is the only way in; the tailnet carries a phone to it from
anywhere. Phase two makes bookdrop an installable PWA with a Web Share Target,
so sharing a downloaded `.acsm` lands on the confirmation screen. Share targets
need a secure context, so this depends on the ingress serving a certificate the
phone trusts. The deployment's is from Let's Encrypt.
