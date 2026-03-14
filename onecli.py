"""
onecli.py — Main entrypoint for the onecli CLI application.

Commands are discovered dynamically from subdirectories inside `commands/`.
Each subdirectory must contain an `__init__.py` that exposes a `command`
object (a click.BaseCommand instance).
"""

import importlib
import os

import click

COMMANDS_DIR = os.path.join(os.path.dirname(__file__), "commands")


class DynamicCommandLoader(click.Group):
    """Discovers and loads click commands from the commands/ directory."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        commands = []
        if not os.path.isdir(COMMANDS_DIR):
            return commands
        for name in sorted(os.listdir(COMMANDS_DIR)):
            path = os.path.join(COMMANDS_DIR, name)
            if os.path.isdir(path) and os.path.isfile(
                os.path.join(path, "__init__.py")
            ):
                commands.append(name)
        return commands

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        try:
            module = importlib.import_module(f"commands.{cmd_name}")
        except ModuleNotFoundError:
            return None
        command = getattr(module, "command", None)
        if command is None:
            raise RuntimeError(
                f"commands/{cmd_name}/__init__.py must expose a `command` object."
            )
        return command


@click.command(cls=DynamicCommandLoader)
def cli() -> None:
    """onecli — a dynamic, plugin-based CLI tool."""


if __name__ == "__main__":
    cli()
