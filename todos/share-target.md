# share-target: a phone's share sheet sends the download straight in

## Opening prompt

> Read `todos/share-target.md` and *Phones* in `docs/design.md`. bookdrop
> serves the steps for an iOS Shortcut at `/shortcut`; what remains is building
> it on the phone and checking it end to end.

## Where it stands

Built on the `share-target` branch, 2026-11-07: `/drop` answers a client asking
for JSON with the confirmation page's path, or the refusal, and `/shortcut`
lists the steps to build the Shortcut, naming the address the phone used.
Checked in the image that day: a JSON drop of the first Kobo book answered
`201` with a path whose page was its confirmation screen, and a text file
`422` with its reason. *Phones* in the design says why it is a Shortcut and
not a Web Share Target.

## Not yet checked

- Whether *Get Contents of URL* hands the Shortcut a `422`'s body or stops with
  an error of its own. Either way the file is refused; only the alert differs.
- Whether Files offers the Shortcut on an `.acsm`, given iOS has no type for it.
  The Shortcut takes any file, so it should.

## Done when

On the phone, *Share → bookdrop* on a downloaded `.acsm` opens the
confirmation screen for that book.
