import nox
import glob

nox.options.reuse_existing_virtualenvs = True
nox.options.reuse_venv = True
nox.options.sessions = ["lint"]

REQUIREMENTS = {
    "dev": "requirements-dev.txt",
    "docs": "docs/requirements.txt",
}

# -----------------------------------------------------------------------------
# Development Commands
# -----------------------------------------------------------------------------


@nox.session()
def lint(session):
    session.install("pre-commit")
    if session.posargs:
        args = session.posargs + ["--all-files"]
    else:
        args = ["--all-files", "--show-diff-on-failure"]

    session.run("pre-commit", "run", *args)


@nox.session(name="test-hook")
def test_hook(session):
    session.install("-e", ".")
    session.install("pre-commit")
    session.run("pre-commit", "try-repo", ".")


@nox.session()
def build(session):
    session.run("python3", "-m", "pip", "wheel", "--no-deps", "-w", "dist", ".")


@nox.session(name="install-wheel", requires=["build"])
def install_wheel(session):
    whl_file = glob.glob("dist/*.whl")
    session.install(str(whl_file[0]))


# @nox.session(name="commit-check", requires=["install-wheel"])
@nox.session(name="commit-check", requires=["install-wheel"])
def commit_check(session):
    session.run(
        "commit-check",
        "--message",
        "--branch",
        "--author-email",
    )


@nox.session(requires=["install-wheel"])
def coverage(session):
    session.run("coverage", "run", "--source", "commit_check", "-m", "pytest")
    session.run("coverage", "report")
    session.run("coverage", "xml")


@nox.session()
def docs(session):
    session.install("-e", ".")
    session.install("-r", REQUIREMENTS["docs"])
    session.run("sphinx-build", "-E", "-W", "-b", "html", "docs", "_build/html")
