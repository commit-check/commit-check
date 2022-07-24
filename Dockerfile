FROM ubuntu:20.04

# WORKDIR option is set by the github action to the environment variable GITHUB_WORKSPACE.
# See https://docs.github.com/en/actions/creating-actions/dockerfile-support-for-github-actions#workdir


LABEL com.github.actions.name="commit check"
LABEL com.github.actions.description="Check each commit with GitHub Action"
LABEL com.github.actions.icon="code"
LABEL com.github.actions.color="gray-dark"

LABEL repository="https://github.com/commit-check/commit-check"
LABEL maintainer="shenxianpeng <20297606+shenxianpeng@users.noreply.github.com>"

RUN apt-get update && apt-get -y install python3-pip

COPY commit_check/ pkg/commit_check/
COPY setup.py pkg/setup.py
RUN python3 -m pip install pkg/

# github action args use the CMD option
# See https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runsargs
# also https://docs.docker.com/engine/reference/builder/#cmd
ENTRYPOINT [ "python3", "-m", "commit_check.main" ]
