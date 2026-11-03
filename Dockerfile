FROM ghcr.io/astral-sh/uv:0.13 AS uv

# libgourou from nixpkgs rather than built here: Debian does not package it, and
# both it and the uPDFParser it builds against come from one self-hosted forge,
# so a source build fails whenever that host is down. This revision's build is
# in cache.nixos.org, and is the same store path devenv provides.
FROM docker.io/nixos/nix:2.35.4 AS libgourou
ARG NIXPKGS=1c89083e451e891152365b799595cf7790a43325
RUN nix --extra-experimental-features "nix-command flakes" build \
    --out-link /libgourou "github:NixOS/nixpkgs/${NIXPKGS}#libgourou" \
  && mkdir -p /closure/nix/store /closure/opt \
  && cp -a $(nix-store --query --requisites /libgourou) /closure/nix/store/ \
  && ln -s "$(readlink -f /libgourou)" /closure/opt/libgourou

FROM docker.io/library/python:3.13-slim

COPY --from=uv /uv /usr/local/bin/uv
COPY --from=libgourou /closure/ /

ENV UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_PROJECT_ENVIRONMENT=/opt/venv \
  PATH=/opt/venv/bin:/opt/libgourou/bin:$PATH

WORKDIR /app

# Dependencies in their own layer, so a source change does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN uv sync --locked --no-dev --no-editable

# Owned by the runtime user, so a named volume mounted here inherits that
# ownership. Kubernetes can fix ownership with fsGroup; Compose cannot.
RUN mkdir /data && chown 1000:1000 /data

USER 1000:1000
EXPOSE 8000
CMD ["bookdrop", "serve"]
