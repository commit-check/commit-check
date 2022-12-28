FROM python:3.10-slim

ARG VERSION==""

LABEL com.github.actions.name="Commit Check"
LABEL com.github.actions.description="Check commit message formatting, branch naming, commit author, email, and more."
LABEL com.github.actions.icon="code"
LABEL com.github.actions.color="gray-dark"

LABEL repository="https://github.com/commit-check/commit-check"
LABEL maintainer="shenxianpeng <20297606+shenxianpeng@users.noreply.github.com>"

RUN if [ -z "${VERSION}" ]; then \
        pip3 install commit-check; \
    else \
        pip3 install commit-check==$VERSION; \
    fi

ENTRYPOINT [ "commit-check" ]
