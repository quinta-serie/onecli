# Contributing to onecli

Thank you for taking the time to contribute! This document explains how to set up your development environment, the project conventions, and the process for submitting changes.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [Coding Conventions](#coding-conventions)
6. [Writing Tests](#writing-tests)
7. [Submitting a Pull Request](#submitting-a-pull-request)
8. [Reporting Bugs and Requesting Features](#reporting-bugs-and-requesting-features)

---

## Code of Conduct

Be respectful, constructive, and inclusive. Harassment of any kind will not be tolerated.

---

## Getting Started

### Prerequisites

- **Docker** — for building and running the containerized CLI.
- **Python 3.13+** — for running tests locally.
- **git** — for version control.

### Fork and clone

```sh
git clone https://github.com/quinta-serie/onecli.git
cd onecli
```

### Install Python dependencies

```sh
pip install -r requirements.txt
```

### Build the Docker image

```sh
./onecli build
```

### Verify everything works

```sh
# Run the test suite
python -m pytest tests/ -v

# Run the built-in example command
./onecli hello --name Contributor
```

---

## Project Structure

```
onecli/
├── Dockerfile              # Container image definition
├── requirements.txt        # Python dependencies (click, pytest)
├── onecli                  # Executable shell wrapper script
├── onecli.py               # Click entrypoint + DynamicCommandLoader
├── common/
│   ├── __init__.py
│   └── config.py           # Config loading (INI file + env vars)
├── commands/
│   ├── __init__.py
│   └── hello/              # Built-in example command plugin
│       └── __init__.py
└── tests/
    ├── __init__.py
    ├── test_config.py      # Tests for config loading & precedence
    └── test_discovery.py   # Tests for command discovery & CLI runner
```

---

## Development Workflow

### Branching strategy

| Branch | Purpose |
|---|---|
| `main` | Stable, release-ready code |
| `feat/<description>` | New features or commands |
| `fix/<description>` | Bug fixes |
| `chore/<description>` | Maintenance, refactoring, docs |

Always branch off `main`:

```sh
git checkout main
git pull origin main
git checkout -b feat/my-new-command
```

### Making changes

1. Make your changes in the appropriate files.
2. If you add or modify a command, rebuild the Docker image: `./onecli build`.
3. Run the tests to make sure nothing is broken: `python -m pytest tests/ -v`.
4. Add new tests for any new behaviour (see [Writing Tests](#writing-tests)).

---

## Coding Conventions

- **Python version:** 3.13+. Use modern Python features (type hints, `match`, etc.).
- **Style:** Follow [PEP 8](https://peps.python.org/pep-0008/). Keep lines ≤ 100 characters.
- **Type hints:** All public functions must have type annotations.
- **Docstrings:** Add a one-line docstring to every `click.command` — it appears in `--help`.
- **Imports:** Standard library → third-party → local, separated by blank lines.
- **Command plugins:**
  - One directory per command under `commands/`.
  - The `__init__.py` must expose exactly one module-level `command` object.
  - Access configuration exclusively through `from common.config import settings`.
  - Never hardcode secrets — document the required `ONECLI_*` env var in the command's docstring.

---

## Writing Tests

Tests live in the `tests/` directory and use `pytest`.

### Test file layout

| File | Covers |
|---|---|
| `tests/test_config.py` | `common/config.py` — settings loading, env var precedence |
| `tests/test_discovery.py` | `onecli.py` — `DynamicCommandLoader`, `list_commands`, `get_command` |

Create a new test file `tests/test_<module>.py` for each new module or command.

### Guidelines

- **Use `monkeypatch`** to isolate filesystem and environment state — never mutate `sys.modules` or `os.environ` directly in tests.
- **Use `click.testing.CliRunner`** to test CLI behaviour end-to-end without spawning processes.
- **Avoid mocking internals** — test observable behaviour (output, exit codes, returned objects).
- **Each test class** should focus on a single concept; each method on a single case.

### Running tests

```sh
# All tests
python -m pytest tests/ -v

# Single file
python -m pytest tests/test_config.py -v

# Single test
python -m pytest tests/test_config.py::TestPrecedence::test_env_var_overrides_rc_file_value -v
```

---

## Submitting a Pull Request

1. **Ensure all tests pass** locally before opening a PR.
2. **Keep PRs focused** — one feature or fix per PR.
3. **Write a clear PR description** that explains:
   - *What* changed.
   - *Why* the change is needed.
   - Any relevant context or trade-offs.
4. **Reference issues** in the description if applicable (`Closes #42`).
5. **Respond to review feedback** promptly and update the branch as needed.

### PR checklist

- [ ] All existing tests pass (`python -m pytest tests/ -v`).
- [ ] New behaviour is covered by new or updated tests.
- [ ] The Docker image builds successfully (`./onecli build`).
- [ ] The command works end-to-end (`./onecli <command>`).
- [ ] Code follows the conventions described above.

---

## Reporting Bugs and Requesting Features

Please open an issue and include:

- A clear, descriptive title.
- Steps to reproduce (for bugs).
- Expected vs. actual behaviour (for bugs).
- The desired behaviour and motivation (for feature requests).
- Your OS, Docker version, and Python version where relevant.
