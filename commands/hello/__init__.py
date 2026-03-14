"""
commands/hello/__init__.py — "hello" example command plugin.

Demonstrates:
  - Reading a default value from the .oneclirc config file.
  - Detecting a secret passed via an ONECLI_* environment variable.
"""

import os

import click

from common.config import settings


def _resolve_default_name() -> str:
    """Return the default name from settings, falling back to 'World'."""
    user_section = settings.get("user", {})
    if isinstance(user_section, dict):
        return user_section.get("default_name", "World")
    return "World"


@click.command(name="hello")
@click.option(
    "--name",
    default=None,
    help="Name to greet.  Defaults to the value of [user] default_name in "
         "~/.oneclirc, or 'World' if not set.",
)
def command(name: str | None) -> None:
    """Greet someone by name."""
    resolved_name = name if name is not None else _resolve_default_name()
    click.echo(f"Hello, {resolved_name}!")

    secret_token = os.getenv("ONECLI_SECRET_TOKEN") or settings.get("secret_token")
    if secret_token:
        click.echo("Secret token found — authenticated mode active.")
    else:
        click.echo("No secret token provided.")
