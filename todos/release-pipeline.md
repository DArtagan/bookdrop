# release-pipeline: the first release, running in the cluster

## Opening prompt

> Read `todos/release-pipeline.md` and `docs/releasing.md`. The scaffold is on
> `main`; get its first release published and running in dry run, with the
> deployment half in the deployment repository (`CLAUDE.local.md` says where).

## Where it stands

On 2026-11-03 the scaffold was pushed, 0.1.0 released from pull request #1 on
branch `release-please--branches--main`, and deployed in dry run. Checked that
day:

- The `v0.1.0` tag and the image's revision label are both `08d28d8`.
- From the desktop on the LAN, `/healthz` over HTTPS reports
  `"dry_run": true`, with a Let's Encrypt certificate that verifies.
- In the pod, the books share lists its 131 author directories and refuses a
  write with `Read-only file system`.

The phone check below is what remains.

## Done when

- `git rev-parse 'v0.1.0^{commit}'` equals the image's
  `org.opencontainers.image.revision` label.
- `/healthz` through the ingress, from a phone on the tailnet, reports
  `"dry_run": true`.
