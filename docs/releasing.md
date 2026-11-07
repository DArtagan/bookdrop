# Releasing and deploying

A release is a deliberate act: merging a commit to `main` does not deploy it.

## How a version is made

1. Commits on `main` follow [Conventional Commits](https://www.conventionalcommits.org/).
   The `convco` commit-msg hook refuses any that do not, because release-please
   reads nothing else.
2. On every push to `main`, release-please updates a standing pull request,
   `chore(main): release X.Y.Z`. It bumps the version in `pyproject.toml`,
   `uv.lock` and the example `compose.yaml`, and writes `CHANGELOG.md` from the
   commits since the last release.
3. Merging that pull request tags `vX.Y.Z` and creates a GitHub release. The
   `publish` job then builds the image **from the tag** and pushes
   `ghcr.io/dartagan/bookdrop:X.Y.Z`, and `latest`.

`release-please-config.json` names no `package-name`, and must not: release-please
puts it into the release branch's name and, unless `include-component-in-tag` is
off, into the tag. Without it the branch is `release-please--branches--main` and
the tag `vX.Y.Z`. The Python strategy reads the package name from
`pyproject.toml` for itself. Releases are immutable once published, so a tag
written with the wrong name stays.

Below 1.0, a breaking change bumps the minor version rather than the major, and
so do `feat` commits; `fix` bumps the patch.

Release PRs are opened by `github-actions`, and GitHub holds CI on them at
*action required* until someone approves the run from the PR. Approving is
optional: they change only versions and the changelog, and CI runs on `main`
once one is merged. Opening them needs the repository setting *Allow GitHub
Actions to create and approve pull requests*.

## Merging a pull request

The pull request's title decides how it is merged. GitHub writes the title into
every merge commit, and release-please reads a Conventional Commit anywhere in a
message.

- **A conventional title** (`fix: …`, `feat: …`) means **squash**. The title
  becomes the one commit on `main` and the one line in the changelog; the
  branch's own commits stay in the pull request. It is the usual case, and the
  only one where a `BEGIN_COMMIT_OVERRIDE` block in the pull request's body can
  correct a note after merging.
- **A plain title**, such as the branch name and a summary, means a **merge
  commit**, for when each commit on the branch belongs in the history. Those
  commits write the notes, and the title writes nothing. The lower of two
  stacked pull requests needs this: squashing it gives `main` a copy of its
  commits, which the branch above then conflicts with.

A merge commit under a conventional title puts every change in the changelog
twice. Retitle the pull request whenever the branch changes which kind it is;
only the title at merge time counts.

## How it reaches the cluster

Flux deploys bookdrop from the deployment repository (see *The deployment
half* in `AGENTS.md`). It polls GHCR, and an `ImagePolicy` with the semver range
`>=0.1.0 <1.0.0` selects the newest release. Flux Bot then commits the new tag
into bookdrop's `Deployment` there. Crossing to 1.0 is a deliberate edit of
that range.

## Checking a release

The tag, the image and the source should all name the same commit:

```bash
git rev-parse 'vX.Y.Z^{commit}'
skopeo inspect docker://ghcr.io/dartagan/bookdrop:X.Y.Z \
  | jq -r '.Labels["org.opencontainers.image.revision"]'
```

The running pod reports its version on `/`.
