# Outstanding work

One self-contained spec per step, each meant to be opened cold in its own
session. A file here means the work has not been done. When it is, its permanent
facts go into `docs/`, the spec is deleted, and
[`docs/project_log.md`](../docs/project_log.md) gets a line. See *Project
workflow* in [`AGENTS.md`](../AGENTS.md).

The design every spec builds on is [`docs/design.md`](../docs/design.md). Specs
name the sections they depend on rather than restating them.

## In order

Dry run stays on until filing, the first spec that writes into the library.
Specs are referred to by name, not number, so finishing one renumbers nothing.

| # | spec | what | needs |
|---|---|---|---|
| 1 | [adept](adept.md) | libgourou in the image and the device key mounted: an uploaded `.acsm` becomes a DRM-free book | — |
| 2 | [confirm](confirm.md) | The upload page and the confirmation screen: metadata read, looked up, edited | adept |
| 3 | [filing](filing.md) | The executor: the book written into the library with its sidecars, and Stump scanning | confirm |
| 4 | [share-target](share-target.md) | An installable PWA, so a phone's share sheet sends the download straight in | confirm |

## Writing a spec

- **State what was verified and when.** Anything not checked says so.
- **Record why, not just what**, and record decisions Will made verbatim, so they
  are not relitigated.
- **Point at the design rather than restating it.** Two copies drift.
- **End with done-when conditions measured in the library or in Stump**, never
  inferred from the service's own report.
- **Include the opening prompt.**
- **Correct in place.** When a finding is overturned, rewrite the passage and
  note the wrong turn if it could be repeated.
