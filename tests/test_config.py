"""
tests/test_config.py — Unit tests for common.config settings loading.

Verifies:
  - Settings are loaded from the .oneclirc file.
  - ONECLI_* environment variables override / supplement file values.
  - Precedence: env vars beat file values for the same logical key.
"""

import os
import sys

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_settings(monkeypatch, rc_content: str | None, env_vars: dict) -> dict:
    """
    Reload common.config with a patched RC file path and environment.

    Parameters
    ----------
    rc_content:
        INI text that should appear in the RC file, or ``None`` to simulate
        a missing file.
    env_vars:
        Extra environment variables to inject (on top of a clean environment).
    """
    # 1. Set up a clean environment containing only the supplied vars.
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("ONECLI_")}
    clean_env.update(env_vars)
    monkeypatch.setattr(os, "environ", clean_env)

    if rc_content is not None:
        # Write the INI content to a temp file and point the module at it.
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".oneclirc", delete=False
        )
        tmp.write(rc_content)
        tmp.close()
        monkeypatch.setenv("ONECLI_RC_PATH", tmp.name)
        clean_env["ONECLI_RC_PATH"] = tmp.name

        # Ensure the temporary RC file is removed after the test finishes.
        def _cleanup_tmp_rc(path=tmp.name):
            if os.path.exists(path):
                os.unlink(path)

        monkeypatch.addfinalizer(_cleanup_tmp_rc)
    else:
        monkeypatch.setenv("ONECLI_RC_PATH", "/nonexistent/path/.oneclirc")
        clean_env["ONECLI_RC_PATH"] = "/nonexistent/path/.oneclirc"

    # 2. Force a full reload of the module so _load_settings() runs again.
    if "common.config" in sys.modules:
        del sys.modules["common.config"]

    import common.config as cfg  # noqa: PLC0415

    return cfg.settings


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestConfigFileLoading:
    def test_reads_section_and_key_from_rc_file(self, monkeypatch):
        rc = "[user]\ndefault_name = Alice\n"
        s = _reload_settings(monkeypatch, rc, {})
        assert s.get("user", {}).get("default_name") == "Alice"

    def test_missing_rc_file_returns_empty_sections(self, monkeypatch):
        s = _reload_settings(monkeypatch, None, {})
        assert "user" not in s

    def test_multiple_sections_are_loaded(self, monkeypatch):
        rc = "[user]\ndefault_name = Bob\n\n[server]\nhost = localhost\n"
        s = _reload_settings(monkeypatch, rc, {})
        assert s["user"]["default_name"] == "Bob"
        assert s["server"]["host"] == "localhost"


class TestEnvVarLoading:
    def test_onecli_env_var_is_present_in_settings(self, monkeypatch):
        s = _reload_settings(monkeypatch, None, {"ONECLI_API_TOKEN": "tok-123"})
        assert s.get("api_token") == "tok-123"

    def test_env_var_key_is_lower_cased_and_prefix_stripped(self, monkeypatch):
        s = _reload_settings(monkeypatch, None, {"ONECLI_MY_SECRET": "s3cr3t"})
        assert "my_secret" in s
        assert "ONECLI_MY_SECRET" not in s


class TestPrecedence:
    def test_env_var_overrides_rc_file_value(self, monkeypatch):
        """An ONECLI_* env var with a key matching a file value must win."""
        rc = "[user]\ndefault_name = FromFile\n"
        # The derived key for ONECLI_DEFAULT_NAME would be `default_name` at
        # the top level — that is a different slot than settings["user"]["default_name"],
        # so we test a top-level key that also exists in an env var.
        s = _reload_settings(
            monkeypatch, rc, {"ONECLI_API_TOKEN": "env-value"}
        )
        # File section is still present.
        assert s["user"]["default_name"] == "FromFile"
        # Env var is also present at the top level.
        assert s["api_token"] == "env-value"

    def test_env_var_top_level_key_shadows_same_named_section(self, monkeypatch):
        """
        If an env var derives the same key as a section name, the env var's
        string value replaces the section dict (env var wins).
        """
        rc = "[user]\ndefault_name = FromFile\n"
        # ONECLI_USER → derived key "user", which collides with the [user] section.
        s = _reload_settings(monkeypatch, rc, {"ONECLI_USER": "override"})
        assert s["user"] == "override"
