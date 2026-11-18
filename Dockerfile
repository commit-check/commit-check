# The Commit Check image: the CLI, git, and commit-check-ci, which checks a
# whole merge or pull request. The GitLab CI/CD component and the Bitbucket
# pipe run it.
#
# Build the wheel first, so the image holds the same file PyPI gets:
#   python -m pip wheel --no-deps -w dist .
#   docker build -t commit-check .
FROM python:3.14-alpine@sha256:5862d971d1f0ae26b258cefa4e893556b1d3aba81bd2ff30888704ad378bab67

LABEL org.opencontainers.image.title="Commit Check" \
      org.opencontainers.image.description="Commit policy as code for teams and AI agents" \
      org.opencontainers.image.url="https://commit-check.com/" \
      org.opencontainers.image.source="https://github.com/commit-check/commit-check" \
      org.opencontainers.image.licenses="MIT"

# commit-check reads commits with git. CI clones or mounts the repository as
# another user than the one the job runs as, which git refuses to read unless
# the directory is marked safe.
RUN apk add --no-cache git \
    && git config --system --add safe.directory '*'

# Install the wheel from the build context and nothing else: no index, no
# dependencies, no source distribution whose setup script would run.
RUN --mount=type=bind,source=dist,target=/dist \
    pip install --no-cache-dir --no-index --no-deps --only-binary :all: \
        --root-user-action=ignore /dist/commit_check-*.whl

COPY --chmod=755 docker/commit_check_ci.py /usr/local/bin/commit-check-ci
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/commit-check-entrypoint

ENTRYPOINT ["commit-check-entrypoint"]
