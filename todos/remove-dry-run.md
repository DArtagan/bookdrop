# remove-dry-run: take the dry-run mode out once filing is live

## Opening prompt

> Read `todos/remove-dry-run.md`. Filing is live and has filed real books, so
> the dry-run mode has done its job. Remove it from the code, the tests, the docs
> and the deployment, keeping the single writer under the books root.

## Why

Will, 2026-11-05: "At the end of this project, let's remove the dry-run code.
It's been nice for development, but long-term would add maintenance drag."

Dry run let bookdrop be deployed, driven from a phone and checked against the
real library before it could write a byte there. Once filing is live it is a
second mode no one runs: every page, test and doc carries both branches, and
the untested one rots. The confirmation screen is the gate a person uses; a
mode switch adds none.

## When

After `filing` closes: books filed for real, seen in Stump, and its spec
retired. Not before, since dry run is what keeps the deployed instance safe
while the books volume is still read-only.

## What goes

On 2026-11-05 dry run appeared in `config.py` (`dry_run`), `executor.py`
(`DryRun` and its check), `web.py` (the plan-only branch, `/healthz`'s
`dry_run`), both templates, `tests/test_web.py` and `tests/test_executor.py`,
and in `README.md`, `AGENTS.md`, `compose.yaml`, `docs/design.md` and
`docs/releasing.md`. `grep -rni 'dry.run'` finds them again. `/healthz` loses a
field, which nothing reads but its tests; check the deployment's probes and
alerts before dropping it.

The deployment loses `BOOKDROP_DRY_RUN`, and the books mount stays writable.

## What stays

- **The executor as the one writer under the books root**, and the test that
  runs every page against a read-only root with the executor replaced. That
  rule is about where writes can come from, not about a mode, and it is what
  stops a stray write elsewhere reaching the library.
- **Planning apart from writing.** `filing.plan()` writes nothing; the
  confirmation page may still list what filing will write before the person
  confirms.

## Done when

`grep -rni 'dry.run'` finds nothing in the repository or in
`kubernetes/apps/bookdrop/` in the deployment repository, a book files from the
phone as before, and the read-only-root test still fails when a stray write is
added outside the executor.
