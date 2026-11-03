# adept: an uploaded .acsm becomes a DRM-free book

## Opening prompt

> Read `todos/adept.md` and *Input* and *Adobe identity* in `docs/design.md`.
> Build libgourou into the image, mount the device key, and turn an uploaded
> `.acsm` into a DRM-free EPUB or PDF under `/data`, refusing anything still
> encrypted.

## Verified 2026-11-03

- **libgourou is not in Debian** (no source package), so the image builds it.
  Upstream is <https://forge.soutade.fr/soutade/libgourou>, active in September
  2026. nixpkgs carries 0.8.9 with all four tools, `adept_activate`,
  `acsmdownloader`, `adept_remove` and `adept_loan_mgt`, and devenv provides
  them. Its build needs pugixml, updfparser, libzip, OpenSSL and curl.
- **`adept_activate -O <dir>`** writes the device key into a directory that
  must not already exist; `-u` takes the Adobe ID's email and prompts for the
  password when `-p` is absent.
- **A Kobo `.acsm`** is a `fulfillmentToken` XML document pointing at
  `acs4.kobo.com`, carrying the title, creator, publisher, format and an
  `expiration` about six hours after purchase.

## The first book

Will's first Kobo purchase, an EPUB, arrived as an `.acsm`
expiring 2026-11-03T11:27Z, before bookdrop could be deployed. The plan is to
activate the dedicated Adobe ID on the desktop and fulfil it there with
`acsmdownloader` against that same device key, so the book belongs to
bookdrop's identity from the start. The encrypted download, kept under
`captures/` on the desktop, is the real input for checking `adept_remove` in
the image. Update this section with what happened.

## The work

- Build libgourou in a builder stage at a pinned upstream tag, and copy the
  three tools and their libraries into the runtime image. CI's image job then
  proves the build on every pull request.
- The device key is mounted read-only. libgourou expects it in a writable
  `.adept` directory, so copy it to a scratch path at startup, if it turns
  out to write there.
- A minimal upload form: `POST` an `.acsm` or an `.epub`. An `.acsm` is fulfilled
  and stripped at once (see the expiry in the design's *Input*).
- Encryption check after stripping: an EPUB carrying a `META-INF/rights.xml`,
  or an `encryption.xml` listing anything other than font obfuscation, is
  refused. The same check refuses an uploaded EPUB that arrives encrypted.
- Tests put stand-in `acsmdownloader` and `adept_remove` scripts on `PATH`, and
  use synthetic EPUBs built in the test, with and without the DRM markers.

## Done when

- The captured encrypted download, run through the image's `adept_remove`,
  opens in Calibre and in KOReader.
- A fresh Kobo `.acsm` uploaded through the deployed form produces a DRM-free
  EPUB under `/data`, and the library is unchanged.
