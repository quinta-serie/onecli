<div align="center">
  <img src="onecli_image.png" alt="onecli logo" width="320" />
  <h1>onecli</h1>
  <p><strong>One CLI to rule them all</strong></p>
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
| [pytest](https://docs.pytest.org/) | Test runner |

### Host machine requirements

| Requirement | Notes |
|---|---|
| **Docker** | Required to build and run the containerized CLI |
| `sh`-compatible shell | The `onecli` wrapper is a POSIX shell script |

Install Python dev dependencies with:

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

### 3. List available commands

```sh
./onecli --help
```

### 4. Get help for a specific command

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

### Expected output

```
15 passed in 0.12s
```

---

## How to Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution guide.

