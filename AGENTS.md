# AGENTS.md

Guidance for coding agents working in this repository.

bookdrop files purchased ebooks into the library Stump reads, stripping Adobe
DRM on the way. [`docs/design.md`](docs/design.md) is the design: the flow from
purchase to library, what it accepts and refuses, the Adobe identity, metadata
and the layout. Read the sections a spec names before changing behaviour.

## Development environment

[devenv](https://devenv.sh/) provides Python 3.13, uv, libgourou, `gh`, `jq` and
`skopeo`. `direnv` loads it on `cd`; otherwise `devenv shell`.

```bash
uv add <package>               # a runtime dependency; --group dev for a test one
pytest                         # the tests
treefmt                        # format the tree
devenv test                    # every hook over every tracked file, as CI runs it
bookdrop serve                 # the web UI on :8000
```

The hooks are the ones `git commit` runs: treefmt, ruff, pytest, and `convco` on
the commit message. Files git does not track are invisible to them; `git add -N`
a new file first.

### Working here as an agent

- **`git diff --no-ext-diff`.** The global git config sends `git diff` through
  difftastic, whose side-by-side output is several times the size.
- **Verify with `devenv test`, not by printing files back.**
- **Filter noisy commands** down to the lines that carry the result.

## Rules that protect the library

- **Dry run is the default, and it must be impossible to bypass by accident.**
  `BOOKDROP_DRY_RUN` is true unless set to `false`. Every write under the books
  root goes through a single executor that checks it. No other code opens
  anything there for writing, and a test holds that line from the moment the
  executor exists.
- **Nothing DRM-locked enters the library.** A file still encrypted after
  stripping is refused, never filed.
- **No real book, `.acsm` or Adobe device key enters the repository.** An `.acsm`
  carries a purchase token; the device key is an account credential. Tests use
  synthetic EPUBs and stand-ins for libgourou's tools. The repository is public.
  Secrets live in the deployment repository, encrypted, and reach the service
  through mounted files or the environment.

## Project workflow

Work is specified in [`todos/`](todos/README.md), one self-contained spec per
step, ordered in that README. A spec's filename without `.md` is its **slug**,
which names the branch it is worked on. Work happens on that branch, in a
worktree made with `wt switch --create <slug>`, and lands on `main` through a
pull request. [`.config/wt.toml`](.config/wt.toml) sets the worktree up; a plain
`git worktree add` skips that and shares git hooks with every other checkout.

When a spec is done, whatever it leaves permanently true goes into `docs/`, and
the spec is deleted in the same pull request, with a line added to
[`docs/project_log.md`](docs/project_log.md). A retired slug is never reused.

Commits follow [Conventional Commits](https://www.conventionalcommits.org/);
release-please builds versions and the changelog from them. Releasing and
deploying are in [`docs/releasing.md`](docs/releasing.md). A merge to `main`
deploys nothing until the release pull request is merged.

### The deployment half

bookdrop runs on a Kubernetes cluster deployed by Flux from a separate GitOps
repository, called **the deployment repository** throughout this one. It holds
bookdrop's manifests, its secrets (the Adobe device key and the Stump API key)
and the books volume, and has its own spec for that half and its own rules for
changing it. A spec here that needs a deployment change says what has to change,
not how that repository is laid out. Where it is checked out is in
`CLAUDE.local.md`, which is not committed.

### Debugging captures

Anything pulled from a running system, such as an `.acsm`, an encrypted
download or logs, goes under `captures/<topic>/` at the root of the checkout.
`.gitignore` excludes it. Whatever a conclusion rests on beyond the session
belongs in a spec or in `docs/` as quoted figures.

## How it is phrased

Comments and docs describe what is, in present tense, and carry the reason where
a reader could otherwise reintroduce a bug. Dates and history belong in specs and
commit messages. A fact lives in one place.
