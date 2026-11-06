# Outstanding work

One self-contained spec per step, each meant to be opened cold in its own
session. A file here means the work has not been done. When it is, its permanent
facts go into `docs/`, the spec is deleted, and
[`docs/project_log.md`](../docs/project_log.md) gets a line. See *Project
workflow* in [`AGENTS.md`](../AGENTS.md).

The design every spec builds on is [`docs/design.md`](../docs/design.md). Specs
name the sections they depend on rather than restating them.

## In order

Dry run is off in the deployment since filing went live, on 2026-11-06, and
its code goes with remove-dry-run.
Specs are referred to by name, not number, so finishing one renumbers nothing.

| # | spec | what | needs |
|---|---|---|---|
| 1 | [share-target](share-target.md) | An installable PWA, so a phone's share sheet sends the download straight in | — |
| 2 | [remove-dry-run](remove-dry-run.md) | Take the dry-run mode out of code, docs and deployment now filing is live, keeping the single writer | — |

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
