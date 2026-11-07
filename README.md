# bookdrop

A drop box for ebooks: upload what the store hands you, from a phone or a
desktop, and it lands in a [Stump](https://www.stumpapp.dev/) library with
confirmed metadata and a consistent layout. An Adobe DRM `.acsm`, as Kobo
sells, is fulfilled and stripped on the way, so the book reads on any device.

It is built for one home server's Kubernetes cluster.

- [docs/design.md](docs/design.md): what it does and why
- [docs/releasing.md](docs/releasing.md): how versions are cut and deployed
- [todos/](todos/README.md): the work remaining, one spec per step

## Running it

[`compose.yaml`](compose.yaml) is an example deployment:

```bash
BOOKS_ROOT=/path/to/books docker compose up -d
```

The web UI is on port 8000.

## Development

```bash
devenv shell                   # Python, uv, libgourou
devenv test                    # every hook over every file, as CI runs it
bookdrop serve                 # the web UI on :8000
```

## Licence

MIT
