FROM ubuntu:22.04

LABEL com.github.actions.name="Commit Check"
LABEL com.github.actions.description="Check each commit with GitHub Action"
LABEL com.github.actions.icon="code"
LABEL com.github.actions.color="gray-dark"

LABEL repository="https://github.com/commit-check/commit-check"
LABEL maintainer="shenxianpeng <20297606+shenxianpeng@users.noreply.github.com>"

RUN apt-get update && apt-get install -y \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /pkg

COPY . .
RUN python3 -m pip install . -r requirements.txt

ENTRYPOINT [ "python3", "-m", "commit_check.main" ]
