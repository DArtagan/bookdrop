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
  must not already exist, and leaves it behind even when activation fails;
  `-u` takes the ByteBooks ID's email and prompts for the password when `-p` is
  absent.
- **A Kobo `.acsm`** is a `fulfillmentToken` XML document pointing at
  `acs4.kobo.com`, carrying the title, creator, publisher, format and an
  `expiration` about six hours after purchase.

## The first book

Will's first Kobo purchase, an EPUB, arrived as an `.acsm` expiring
2026-11-03T11:27Z, before bookdrop could fulfil anything. On 2026-11-03 it was
fulfilled on the desktop, against the device key the deployment holds, with
nixpkgs' libgourou 0.8.9:

- `acsmdownloader -D <key dir> -O <dir> <file>.acsm` wrote `<Title>.epub`,
  1.3 MB, named from the `.acsm`'s title.
- It carried `META-INF/rights.xml` and an `encryption.xml` listing 38 entries,
  all `http://www.w3.org/2001/04/xmlenc#aes128-cbc`.
- `adept_remove -D <key dir> <file>`, which strips in place unless given `-o`
  or `-O`, left neither file.
- Calibre converted the result to 85,913 words of text with no control
  characters, so it was decrypted rather than merely unmarked.

The encrypted download is in the primary checkout's
`captures/fulfilled/`, and the `.acsm` beside it in `captures/acsm/`. That
`.acsm` is spent; a second fulfilment of it was not tried.

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
  comes out byte-identical to the desktop's stripped copy, or failing that
  opens in Calibre and in KOReader.
- A fresh Kobo `.acsm` uploaded through the deployed form produces a DRM-free
  EPUB under `/data`, and the library is unchanged.
