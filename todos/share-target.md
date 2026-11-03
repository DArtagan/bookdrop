# share-target: a phone's share sheet sends the download straight in

## Opening prompt

> Read `todos/share-target.md` and *Phones* in `docs/design.md`. Make bookdrop an
> installable PWA whose Web Share Target accepts an `.acsm` or `.epub`, so
> sharing a store download lands on the confirmation screen.

## The work

- A web app manifest with `share_target` (`method: POST`,
  `enctype: multipart/form-data`, `files` accepting the two types), and the
  service worker installability needs.
- Share targets and service workers need a secure context. The deployment's
  certificate is from Let's Encrypt (issued 2026-11-03), which phones trust.
- Web Share Target is supported by Chrome on Android, not by Safari on iOS, as
  far as was known on 2026-11-03 (unverified). On iOS, a Shortcut that posts the
  file is the fallback.

## Done when

On the phone, *Share → bookdrop* on a downloaded `.acsm` opens the
confirmation screen for that book.
