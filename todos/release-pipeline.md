# release-pipeline: the first release, running in the cluster

## Opening prompt

> Read `todos/release-pipeline.md` and `docs/releasing.md`. The scaffold is on
> `main`; get its first release published and running in dry run, with the
> deployment half in the deployment repository (`CLAUDE.local.md` says where).

## Where it stands

The scaffold was pushed on 2026-11-03: a FastAPI app serving `/` and
`/healthz`, the image build, CI and release-please, copied from reelbarrow's
proven pipeline. The repository settings match reelbarrow's.

## The work

1. Merge release-please's first pull request once CI on `main` is green. Its
   branch must be `release-please--branches--main`; one with `--components--` in
   it means a `package-name` crept into the config (see `docs/releasing.md`).
2. In the deployment repository: a `Deployment` with `BOOKDROP_DRY_RUN` unset,
   the books volume mounted read-only at `/books`, a volume at `/data`, a
   `Service`, an internal `Ingress` that allows uploads larger than the
   ingress's default body size, and image automation with the semver range
   `>=0.1.0 <1.0.0`.

## Done when

- `git rev-parse 'v0.1.0^{commit}'` equals the image's
  `org.opencontainers.image.revision` label.
- `/healthz` through the ingress, from a phone on the tailnet, reports
  `"dry_run": true`.
