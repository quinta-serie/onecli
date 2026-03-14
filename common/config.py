"""
common/config.py — Configuration loader for onecli.

Settings are merged from two sources with the following precedence
(highest wins):

    1. Environment variables prefixed with ``ONECLI_``
    2. INI-formatted config file at ``/root/.oneclirc`` (inside the container)

The ``settings`` dict is the single public interface.  Keys for env-var
entries are derived by lower-casing the variable name and stripping the
``ONECLI_`` prefix, e.g. ``ONECLI_API_TOKEN`` → ``api_token``.

INI file values are accessible as ``settings[section][key]`` while
env-var values live at the top level as ``settings[derived_key]``.
"""

import configparser
import os

RC_FILE_PATH = os.environ.get("ONECLI_RC_PATH", "/root/.oneclirc")


def _load_settings() -> dict:
    config: dict = {}

    # --- Layer 1: .oneclirc file (lowest precedence) ---
    parser = configparser.ConfigParser()
    if os.path.isfile(RC_FILE_PATH):
        parser.read(RC_FILE_PATH)
        for section in parser.sections():
            config[section] = dict(parser[section])

    # --- Layer 2: ONECLI_* environment variables (highest precedence) ---
    for key, value in os.environ.items():
        if key.startswith("ONECLI_") and key != "ONECLI_RC_PATH":
            derived_key = key[len("ONECLI_"):].lower()
            config[derived_key] = value

    return config


settings: dict = _load_settings()

def settings_for_command(command_name: str) -> dict:
    """
    Return a dict of settings relevant to a specific command, merging any
    command-specific keys with the global ones.  Command-specific keys take
    precedence over global ones.

    For example, for a command named "hello", settings from the "hello"
    section in the config file would override any clashing top-level env-var
    keys.
    """
    if not isinstance(settings, dict):
        return {}
    return settings.get(command_name, {})
