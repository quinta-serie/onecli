"""
tests/test_discovery.py — Unit tests for DynamicCommandLoader command discovery.

Verifies:
  - Only subdirectories that contain an __init__.py are listed as commands.
  - An unknown command name returns None from get_command().
  - Discovered commands are invokable via the CLI runner.
"""

import sys
import types

import click
import pytest
from click.testing import CliRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_loader(commands_path: str) -> type:
    """
    Return a fresh DynamicCommandLoader class whose COMMANDS_DIR points to
    the given path.  We reload onecli.py with the patched constant so we get
    an isolated class.
    """
    onecli_mod = importlib.import_module("onecli")
    onecli_mod = importlib.reload(onecli_mod)

    # Patch the module-level constant.
    onecli_mod.COMMANDS_DIR = commands_path
    return onecli_mod.DynamicCommandLoader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def fake_commands_dir(tmp_path):
    """
    Create a temporary commands/ directory with two valid plugins and one
    entry that must *not* be discovered (no __init__.py).
    """
    for name in ("alpha", "beta"):
        pkg = tmp_path / name
        pkg.mkdir()
        (pkg / "__init__.py").write_text(
            "import click\n\n"
            f"@click.command(name='{name}')\n"
            f"def command():\n"
            f"    click.echo('ran {name}')\n"
        )

    # A lone file — must be ignored.
    (tmp_path / "not_a_command.txt").write_text("ignored")

    # A directory without __init__.py — must be ignored.
    (tmp_path / "incomplete").mkdir()

    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestListCommands:
    def test_discovers_valid_command_subdirectories(self, fake_commands_dir):
        Loader = _make_loader(str(fake_commands_dir))
        ctx = click.Context(click.Command("root"))
        loader = Loader()
        found = loader.list_commands(ctx)
        assert "alpha" in found
        assert "beta" in found

    def test_ignores_non_directory_entries(self, fake_commands_dir):
        Loader = _make_loader(str(fake_commands_dir))
        ctx = click.Context(click.Command("root"))
        loader = Loader()
        found = loader.list_commands(ctx)
        assert "not_a_command.txt" not in found

    def test_ignores_directories_without_init(self, fake_commands_dir):
        Loader = _make_loader(str(fake_commands_dir))
        ctx = click.Context(click.Command("root"))
        loader = Loader()
        found = loader.list_commands(ctx)
        assert "incomplete" not in found

    def test_returns_empty_list_when_commands_dir_missing(self, tmp_path):
        Loader = _make_loader(str(tmp_path / "nonexistent"))
        ctx = click.Context(click.Command("root"))
        loader = Loader()
        assert loader.list_commands(ctx) == []

    def test_commands_are_sorted(self, fake_commands_dir):
        Loader = _make_loader(str(fake_commands_dir))
        ctx = click.Context(click.Command("root"))
        found = Loader().list_commands(ctx)
        assert found == sorted(found)


def _patch_commands_pkg(monkeypatch, fake_commands_dir):
    """
    Replace the ``commands`` package in sys.modules with a stub that points
    to `fake_commands_dir`, and purge any already-loaded ``commands.*``
    submodules.  monkeypatch ensures everything is restored after the test.
    """
    pkg = types.ModuleType("commands")
    pkg.__path__ = [str(fake_commands_dir)]  # type: ignore[attr-defined]
    pkg.__package__ = "commands"
    monkeypatch.setitem(sys.modules, "commands", pkg)
    for key in list(sys.modules.keys()):
        if key.startswith("commands."):
            monkeypatch.delitem(sys.modules, key, raising=False)


class TestGetCommand:
    def test_returns_none_for_unknown_command(self, fake_commands_dir):
        Loader = _make_loader(str(fake_commands_dir))
        ctx = click.Context(click.Command("root"))
        result = Loader().get_command(ctx, "does_not_exist")
        assert result is None

    def test_returns_command_for_valid_name(self, fake_commands_dir, monkeypatch):
        _patch_commands_pkg(monkeypatch, fake_commands_dir)

        Loader = _make_loader(str(fake_commands_dir))
        ctx = click.Context(click.Command("root"))
        cmd = Loader().get_command(ctx, "alpha")
        assert cmd is not None
        assert isinstance(cmd, click.Command)


class TestCLIRunner:
    def test_cli_lists_discovered_commands_in_help(
        self, fake_commands_dir, monkeypatch
    ):
        _patch_commands_pkg(monkeypatch, fake_commands_dir)

        onecli_mod = importlib.import_module("onecli")
        onecli_mod = importlib.reload(onecli_mod)

        onecli_mod.COMMANDS_DIR = str(fake_commands_dir)

        runner = CliRunner()
        result = runner.invoke(onecli_mod.cli, ["--help"])
        assert result.exit_code == 0
        assert "alpha" in result.output
        assert "beta" in result.output
