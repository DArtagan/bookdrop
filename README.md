# bookdrop

A drop box for ebooks: upload what the store hands you, from a phone or a
desktop, and it lands in a [Stump](https://www.stumpapp.dev/) library with
confirmed metadata and a consistent layout. An Adobe DRM `.acsm`, as Kobo
sells, is fulfilled and stripped on the way, so the book reads on any device.

It is built for one person's home server, and that shapes what it assumes;
see [Before you run it](#before-you-run-it).

- [docs/design.md](docs/design.md): what it does and why
- [docs/releasing.md](docs/releasing.md): how versions are cut and deployed
- [todos/](todos/README.md): the work remaining, one spec per step

## How it works

1. Buy an ebook. Where a store offers a choice, take **Adobe DRM**; Readium LCP
   cannot be read.
2. Drop the download, an `.acsm`, an EPUB or a PDF, on bookdrop's page. An
   `.acsm` is fulfilled from the store at once, since it expires within hours
   and belongs to the first device that fulfils it.
3. Check the metadata it read from the book, with gaps filled from
   [Open Library](https://openlibrary.org/) by ISBN, and the folder it will go
   to. Edit anything.
4. **File it.** bookdrop writes the book, `cover.jpg` and `metadata.opf` into
   `Author/[Series/]Title/` under the library, never over an existing book, and
   asks Stump to scan.

On an iPhone, bookdrop's own `/shortcut` page lists the steps to build a
Shortcut that puts bookdrop in the share sheet; Safari cannot add a site there
itself.

## Before you run it

- **It has no login.** Anyone who can reach it can write books into your
  library. Run it where only you can reach it: a home network, a VPN, or behind
  a reverse proxy that authenticates.
- **It removes DRM**, from Adobe ADEPT books, with
  [libgourou](https://forge.soutade.fr/soutade/libgourou). Whether that is
  lawful where you are, even for books you bought, is for you to establish.
  Readium LCP and Kindle books are refused.
- **It is written for Stump.** Any library directory works, but only Stump is
  asked to scan, and the metadata is written in the forms Stump reads.
- **Folder and file names are ASCII.** `Miéville` is filed as `Mieville`, so
  names read the same over any share and character set; the book's own
  metadata keeps the real spelling.
- **The image is `linux/amd64` only.**

## Running it

```bash
docker run -d -p 8000:8000 \
  -v /path/to/books:/books \
  -v bookdrop-data:/data \
  -v /path/to/adept:/adept:ro \
  -e BOOKDROP_STUMP_URL=http://stump:10801 \
  -e BOOKDROP_STUMP_API_KEY=... \
  -e BOOKDROP_STUMP_LIBRARY_ID=... \
  ghcr.io/dartagan/bookdrop
```

[`compose.yaml`](compose.yaml) is the same as a Compose file. The page is on
port 8000, and `/healthz` answers `200` when it is up. The container runs as
uid 1000, which must be able to write the library.

A reverse proxy in front must accept uploads larger than its default body
limit, which an ebook often exceeds: in ingress-nginx,
`nginx.ingress.kubernetes.io/proxy-body-size: "0"`.

### Settings

| Variable | Default | What it is |
|---|---|---|
| `BOOKDROP_BOOKS_ROOT` | `/books` | The library. Books are filed beneath it. |
| `BOOKDROP_DATA_DIR` | `/data` | Drops awaiting confirmation, the record of each drop, and `authors.toml`. Keep it on a volume. |
| `BOOKDROP_ADEPT_DIR` | `/adept` | The Adobe device key, below. Without it, DRM-free books still work. |
| `BOOKDROP_STUMP_URL` | unset | Stump's address, as bookdrop reaches it. |
| `BOOKDROP_STUMP_API_KEY` | unset | A Stump API key, below. |
| `BOOKDROP_STUMP_LIBRARY_ID` | unset | The Stump library to scan: the id in its page's address, `/libraries/<id>`. |

Unset, the three Stump settings leave filing as it is, and the page says that
Stump was not asked; scan from Stump instead.

`authors.toml` in the data directory, optional, maps spellings of an author to
one name, and is read on every request:

```toml
[aliases]
"T. A. Pratt" = "Tim Pratt"
```

### The Adobe device key

An `.acsm` is fulfilled to a device that Adobe's DRM service knows. Make one,
once, on any machine with libgourou, and give bookdrop its three files.

1. Create an account at <https://dtsbytebooks.com/register>, used for nothing
   else. Adobe handed its ebook DRM service to ByteBooks in 2025, and a new
   Adobe ID cannot activate a device.
2. Run `adept_activate -u <that account's email> -O <a new directory>` and give
   the password when asked. With Nix, it is in `nixpkgs#libgourou`.
3. Mount the directory, holding `device.xml`, `activation.xml` and
   `devicesalt`, at `/adept`, read-only. Keep a copy: an account can activate
   only a limited number of devices, and every book is fulfilled to this one.

### The Stump API key

In Stump's settings, under API keys, create a key with **Explicit
Permissions**, granting **Scan Libraries** alone, and no expiry. The account
creating it needs the *API Keys* permission.

## Development

```bash
devenv shell                   # Python, uv, libgourou
devenv test                    # every hook over every file, as CI runs it
bookdrop serve                 # the web UI on :8000
```

## Licence

MIT
