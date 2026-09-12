# Contributions are welcome!

This repository is the `vsdxkit` fork of
[dave-howard/vsdx](https://github.com/dave-howard/vsdx). The distribution
installs as `vsdxkit` and imports as `vsdx`. Python 3.10 or later is required.

#### Development environment

The repository uses [uv](https://docs.astral.sh/uv/) with a committed lockfile:

```
uv sync --extra docs    # test, lint and build groups plus Sphinx
uv run pytest tests -q
uv run ruff check vsdx tests
uv run ruff format --check vsdx tests
uv run pyrefly check vsdx --min-severity warn
uv run zizmor .github/workflows
uv run sphinx-build -W --keep-going -b html docs docs/_build/html
```

CI runs exactly these gates, plus a lowest-direct dependency-floor job and a
distribution build-and-smoke-test, across Python 3.10–3.14 on Linux and
Windows. Please make sure they pass locally before submitting.

Commit messages follow Conventional Commits (`feat:`, `fix:`, `docs:`, `ci:`,
`chore:`), matching the existing history.

#### Ideas / Features
If you have ideas for new features or improvements please raise a new
issue (_though please do check existing issues_).

If you would like to see an existing feature request delivered - please
comment on the issue.

If you identify a problem - then please raise a new issue with details
on how to recreate the problem so it can be resolved. If you are able
to provide a failing test case that would be super helpful :)

#### Code contributions
If you want to work on an existing issue please comment your intent on
the issue in case someone else is already actively working on it.

Feel free to fork, develop and submit pull requests. I will try to be
responsive - but apologies in advance if I am not!

Please add new tests for any new features you create, and keep the
existing type-checking and formatting gates green.

#### Upstream
This repository is a fork and its history is periodically reconciled with
upstream. If your change would also benefit the original project, consider
opening it at <https://github.com/dave-howard/vsdx> first — but issues and
pull requests here are just as welcome.

#### Security
Please report vulnerabilities privately — see [SECURITY.md](SECURITY.md).

Thank you :)
