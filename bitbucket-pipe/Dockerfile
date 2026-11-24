# The Commit Check pipe for Bitbucket Pipelines: commit-check-ci in a container.
# Build it from this directory, next to a requirements.txt that pins
# commit-check by hash; the release workflow writes one for every release.
FROM python:3.15-alpine@sha256:0f9552bb28711333da16915ec146f5e6bb44a7fdac9ced15dc17c2e0206346dd

LABEL org.opencontainers.image.title="Commit Check pipe" \
      org.opencontainers.image.description="Bitbucket Pipelines pipe that checks a pull request's branch, title, description and every commit against the rules in cchk.toml." \
      org.opencontainers.image.url="https://commit-check.com/" \
      org.opencontainers.image.documentation="https://bitbucket.org/commit-check/commit-check" \
      org.opencontainers.image.source="https://github.com/commit-check/commit-check" \
      org.opencontainers.image.licenses="MIT"

# Pipelines mounts the clone into the pipe's container owned by another user,
# and git refuses to read a repository it does not own unless told to trust it.
RUN apk add --no-cache git \
 && git config --system --add safe.directory '*'

# A wheel next to the requirements file is installed instead of the one on
# PyPI; CI uses that to test a build that is not released yet.
COPY requirements.txt *.whl /tmp/pipe/
RUN pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore \
      --require-hashes --only-binary :all: -r /tmp/pipe/requirements.txt \
 && rm -rf /tmp/pipe

COPY pipe.sh /pipe.sh

# Not root. Pipelines checks out with umask 000, so the clone is writable to
# any user; the rebase check writes the destination branch's ref into it.
RUN adduser -D -H -u 10001 pipe
USER pipe

ENTRYPOINT ["/pipe.sh"]
