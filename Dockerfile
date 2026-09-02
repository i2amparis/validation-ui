FROM debian:bookworm-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Authenticate git access to github.com, both for `uv sync` below (which
# fetches vetting-adapter/nomenclature-adapter by pinned commit SHA) and at
# runtime (nomenclature_adapter's own git clone/fetch of this app's
# definitions repositories, all hosted on github.com too) -- anonymous git
# access to github.com from this host has been intermittently failing
# (rate-limiting or similar), taking down both the build and the running
# app. Every repository involved is public, so a token with no scopes /
# public-repo-read-only is sufficient.
#
# `x-access-token` is a placeholder username (the convention GitHub Actions
# itself uses) -- a bare `https://<token>@github.com/` (token as username,
# no password half) is NOT enough on its own: GitHub's git backend accepts
# the token as either half of a user:password pair, but only if BOTH halves
# are present in the URL; git then fails trying to prompt for the missing
# password in a non-interactive build.
#
# NB! Dokku does NOT automatically pass `config:set` vars through as
# matching `ARG`s for a Dockerfile-based build -- that has to be done
# explicitly:
#   dokku config:set <app> GITHUB_TOKEN=<token>
#   dokku docker-options:add <app> build "--build-arg GITHUB_TOKEN=$(dokku config:get <app> GITHUB_TOKEN)"
# A locally-run `docker build .` with no token set behaves exactly as
# before (anonymous access).
ARG GITHUB_TOKEN
RUN if [ -n "$GITHUB_TOKEN" ]; then \
      git config --global url."https://x-access-token:${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"; \
    fi

RUN uv sync

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["uv", "run", "streamlit", "run", "ui/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
