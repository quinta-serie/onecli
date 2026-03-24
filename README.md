<div align="center">
  <img src="onecli_image.png" alt="onecli logo" width="320" />
  <h1>onecli</h1>
  <p><strong>One CLI to rule them all</strong></p>
</div>

[![CI](https://github.com/quinta-serie/onecli/actions/workflows/ci.yml/badge.svg?branch=main&event=push)](https://github.com/quinta-serie/onecli/actions/workflows/ci.yml)

<div align="center">
  <p>A dynamic, plugin-based command-line tool — fully containerized so it runs anywhere with zero local Python setup.</p>
</div>

`onecli` is a framework for building a single, unified CLI tool out of independent command plugins. Each command lives in its own subdirectory under `commands/` and is discovered automatically at runtime — no registration, no hardcoded imports.

The entire application runs inside a Docker container, ensuring consistent behaviour across every machine and OS. A thin shell wrapper script (`onecli`) abstracts all Docker plumbing so callers interact with a normal CLI experience.

Configuration is handled through two sources with a clear precedence model:

| Source | Precedence | Use for |
|---|---|---|
| `ONECLI_*` environment variables | **High** | Secrets, CI overrides |
| `~/.oneclirc` INI file | Low | Personal defaults |

---

## Dependencies

### Runtime (inside the container)

| Dependency | Purpose |
|---|---|
| Python 3.13 | Language runtime |
| [click](https://click.palletsprojects.com/) | CLI framework |

### Development / Testing (local)

| Dependency | Purpose |
|---|---|
| [pytest](https://docs.pytest.org/) | Test runner (installed in the container image via `requirements.txt`) |

### Host machine requirements

| Requirement | Notes |
|---|---|
| **Docker** | Required to build and run the containerized CLI |
| `sh`-compatible shell | The `onecli` wrapper is a POSIX shell script |

> Note: The Docker image installs all Python dependencies from `requirements.txt`, including `pytest`. While `pytest` is primarily used for development and testing, it is present inside the runtime container as well.

Install Python dev dependencies locally with:

```sh
pip install -r requirements.txt
```

---

## How It Works

```
┌────────────────────────────────────────────────┐
│  Host machine                                  │
│                                                │
│  $ ./onecli hello --name Alice                 │
│        │                                       │
│        ▼                                       │
│  onecli (shell script)                         │
│    • mounts ~/.oneclirc (if present)           │
│    • forwards ONECLI_* env vars                │
│    • docker run --rm onecli-app ...            │
│        │                                       │
└────────┼───────────────────────────────────────┘
         │
┌────────▼───────────────────────────────────────┐
│  Docker container (onecli-app)                 │
│                                                │
│  python onecli.py hello --name Alice           │
│        │                                       │
│        ▼                                       │
│  DynamicCommandLoader                          │
│    • scans commands/ for subdirs               │
│    • imports commands.<name>.command           │
│        │                                       │
│        ▼                                       │
│  commands/hello/__init__.py :: command()       │
│    • reads settings from common/config.py      │
│    • prints greeting                           │
└────────────────────────────────────────────────┘
```

### Key components

| File | Responsibility |
|---|---|
| `onecli` | Shell wrapper — Docker entry point for the host |
| `onecli.py` | Click entrypoint + `DynamicCommandLoader` |
| `common/config.py` | Merges `.oneclirc` file and `ONECLI_*` env vars into `settings` |
| `commands/<name>/__init__.py` | Self-contained command plugin |

### Wrapper script subcommands

| Subcommand | Description |
|---|---|
| `build` | Builds the Docker image (`docker build -t onecli-app .`) |
| `dev <cmd>` | Mounts the local project directory into the container — code changes take effect without rebuilding |
| `shell` | Opens an interactive `sh` session inside the container for debugging |
| *(any other)* | Runs the specified command inside the container normally |

### Configuration precedence

`common/config.py` runs at startup and builds a single `settings` dict:

1. Reads all `[section]` keys from `/root/.oneclirc` (INI format).
2. Reads every `ONECLI_*` environment variable, strips the prefix, lower-cases the key, and merges it at the top level — **overriding** any same-named section from step 1.

Example: `ONECLI_USER=override` replaces the entire `[user]` section from the file.

---

## How to Extend (Adding New Commands)

Adding a new command requires only **one new directory and one Python file**.

### Steps

1. **Create the command directory:**

   ```sh
   mkdir commands/mycommand
   ```

2. **Create `commands/mycommand/__init__.py`** and expose a `command` object:

   ```python
   import click
   from common.config import settings

   @click.command(name="mycommand")
   @click.option("--verbose", is_flag=True, help="Enable verbose output.")
   def command(verbose: bool) -> None:
       """Short description shown in --help."""
       if verbose:
           click.echo(f"Settings loaded: {settings}")
       click.echo("mycommand executed!")
   ```

3. **Rebuild the Docker image** to include the new file:

   ```sh
   ./onecli build
   ```

4. **Run it:**

   ```sh
   ./onecli mycommand --verbose
   ```

### Rules for plugins

- The directory name becomes the CLI sub-command name.
- The `__init__.py` **must** expose a module-level object named exactly `command`.
- It must be a `click.Command` instance (decorated with `@click.command()`).
- Access shared configuration via `from common.config import settings`.
- Secrets should be passed as `ONECLI_*` env vars — never hardcoded.

---

## Available Commands

| Command | Description | Documentation |
|---|---|---|
| `hello` | Example greeting command — demonstrates config and env var integration | built-in |
| `senior-stock` | Fetches and displays stock data from the Senior stock API | [senior-stock](commands/senior-stock/README.md) |
| `tesseract` | Fetches and displays product variation data from the Tesseract API | [tesseract](commands/tesseract/README.md) |

---

## How to Use

### 1. Build the Docker image

```sh
./onecli build
```

This runs `docker build -t onecli-app .` under the hood.

### 2. Run a command

```sh
./onecli <command> [OPTIONS]
```

#### Built-in example — `hello`

```sh
# Default greeting
./onecli hello
# Hello, World!

# Override the name via CLI option
./onecli hello --name Alice
# Hello, Alice!

# Override the name via ~/.oneclirc
cat ~/.oneclirc
# [user]
# default_name = Bob
./onecli hello
# Hello, Bob!

# Pass a secret token via environment variable
ONECLI_SECRET_TOKEN=my-secret ./onecli hello
# Hello, World!
# Secret token found — authenticated mode active.
```

### 3. Develop without rebuilding (`dev` mode)

During active development, use the `dev` subcommand to mount your local source directory directly into the running container. This means code changes are reflected immediately — no `docker build` needed between iterations.

```sh
./onecli dev <command> [OPTIONS]
```

Example:

```sh
./onecli dev hello --name Alice
```

Under the hood this runs:

```sh
docker run --rm -v <project-dir>:/app onecli-app hello --name Alice
```

> **Note:** you still need to run `./onecli build` at least once before using `dev` mode, and again whenever `requirements.txt` or the `Dockerfile` changes.

### 4. Open an interactive shell in the container (`shell` mode)

Use the `shell` subcommand to drop into an interactive `sh` session inside the container. Useful for debugging, inspecting the filesystem, or running one-off Python commands.

```sh
./onecli shell
```

The container starts with the same `~/.oneclirc` mount and `ONECLI_*` env vars as a normal run, but the entrypoint is replaced with `sh` and the session is interactive (`-it`).

### 5. List available commands

```sh
./onecli --help
```

### 6. Get help for a specific command

```sh
./onecli hello --help
```

### Configuration file (`~/.oneclirc`)

Create an INI-formatted file at `~/.oneclirc` on your host machine:

```ini
[user]
default_name = YourName

[server]
host = api.example.com
```

It is automatically mounted into the container as read-only.

### Environment variables

Any variable prefixed with `ONECLI_` on the host is forwarded into the container:

```sh
export ONECLI_SECRET_TOKEN="my-secret-token"
export ONECLI_API_KEY="key-abc123"
./onecli hello
```

---

## How to Test

Tests are written with `pytest` and run **locally** (outside Docker), so Python must be available.

### Install test dependencies

```sh
pip install -r requirements.txt
```

### Run the full test suite

```sh
python -m pytest tests/ -v
```

### Run a specific test file

```sh
# Configuration loading tests
python -m pytest tests/test_config.py -v

# Command discovery tests
python -m pytest tests/test_discovery.py -v
```

### Test coverage overview

| Test file | What it covers |
|---|---|
| `tests/test_config.py` | INI file parsing, env var loading, precedence rules |
| `tests/test_discovery.py` | Directory scanning, `__init__.py` detection, `get_command`, CLI runner |

---

## How to Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution guide.

