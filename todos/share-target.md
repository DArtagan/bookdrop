# share-target: a phone's share sheet sends the download straight in

## Opening prompt

> Read `todos/share-target.md` and *Phones* in `docs/design.md`. bookdrop
> serves the steps for an iOS Shortcut at `/shortcut`; what remains is building
> it on the phone and checking it end to end.

## Where it stands

Built and released in 0.6.0, 2026-11-07, and tried on the phone the same day:

- Files offers the Shortcut on an `.acsm`, and the upload reaches `/drop`.
- A file bookdrop refuses comes back as an alert with bookdrop's reason.
- The confirmation page did not open: the Shortcut opened bookdrop's front page,
  having joined an empty path to the address. `/drop` now answers with the full
  URL, which the Shortcut opens as it is, and `/shortcut`'s steps say so
  (branch `shortcut-url`). The phone's Shortcut needs its steps 4 to 6 rebuilt
  to match.

## Done when

On the phone, *Share → bookdrop* on a downloaded `.acsm` opens the
confirmation screen for that book.
