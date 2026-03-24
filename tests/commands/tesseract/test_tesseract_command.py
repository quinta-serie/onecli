"""
tests/commands/tesseract/test_tesseract_command.py
Unit tests for commands/tesseract/tesseract_command.py

Covers:
  - command (CLI) — happy path, --show-only filter (blocked/unblocked/all),
                    --quiet flag, 404 HTTPError handled, other HTTPError re-raised,
                    empty modelVariations, missing modelVariations key,
                    multiple variations, block reasons joined, totals output,
                    BU and MODEL arguments
"""

import sys
import types
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

_TESSERACT_DIR = str(
    Path(__file__).parent.parent.parent.parent / "commands" / "tesseract"
)
_PKG_NAME = "tesseract_cmd"

_MOCK_SETTINGS = {
    "tesseract_fisia_url":    "https://fisia.example.com/api/",
    "tesseract_centauro_url": "https://centauro.example.com/api/",
}


# ---------------------------------------------------------------------------
# Module loader
# ---------------------------------------------------------------------------

def _load_cmd_module():
    """
    Load commands/tesseract/tesseract_command.py as part of a proper Python
    package so that ``from .tesseract_api import TesseractAPI`` resolves.
    """
    for key in list(sys.modules):
        if key == _PKG_NAME or key.startswith(_PKG_NAME + "."):
            del sys.modules[key]

    # 1. Package stub
    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [_TESSERACT_DIR]
    pkg.__package__ = _PKG_NAME
    pkg.__name__ = _PKG_NAME
    sys.modules[_PKG_NAME] = pkg

    # 2. Load tesseract_api.py as submodule
    api_spec = importlib.util.spec_from_file_location(
        f"{_PKG_NAME}.tesseract_api",
        Path(_TESSERACT_DIR) / "tesseract_api.py",
    )
    api_mod = importlib.util.module_from_spec(api_spec)
    api_mod.__package__ = _PKG_NAME
    sys.modules[f"{_PKG_NAME}.tesseract_api"] = api_mod
    api_spec.loader.exec_module(api_mod)

    # 3. Load tesseract_command.py as submodule
    cmd_spec = importlib.util.spec_from_file_location(
        f"{_PKG_NAME}.tesseract_command",
        Path(_TESSERACT_DIR) / "tesseract_command.py",
        submodule_search_locations=[_TESSERACT_DIR],
    )
    cmd_mod = importlib.util.module_from_spec(cmd_spec)
    cmd_mod.__package__ = _PKG_NAME
    sys.modules[f"{_PKG_NAME}.tesseract_command"] = cmd_mod

    with patch("common.config.settings_for_command", return_value=_MOCK_SETTINGS):
        cmd_spec.loader.exec_module(cmd_mod)

    return cmd_mod


_cmd = _load_cmd_module()

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

_PRODUCT_UNBLOCKED = {
    "sku": "SKU001",
    "externalId": "EXT001",
    "blocked": False,
    "stock": {"available": 10, "total": 15},
    "blockReasons": [],
}

_PRODUCT_BLOCKED = {
    "sku": "SKU002",
    "externalId": "EXT002",
    "blocked": True,
    "stock": {"available": 0, "total": 5},
    "blockReasons": ["reason_a", "reason_b"],
}

_BOTH_PRODUCTS_DATA = {
    "modelVariations": [
        {"products": [_PRODUCT_UNBLOCKED, _PRODUCT_BLOCKED]}
    ]
}


# ---------------------------------------------------------------------------
# Helper: invoke CLI
# ---------------------------------------------------------------------------

def _invoke(args=None, fetch_data_return=None):
    runner = CliRunner()
    data = fetch_data_return if fetch_data_return is not None else _BOTH_PRODUCTS_DATA

    mock_api_instance = MagicMock()
    mock_api_instance.fetch_data.return_value = data
    mock_api_cls = MagicMock(return_value=mock_api_instance)

    with patch.object(_cmd, "TesseractAPI", mock_api_cls), \
         patch("common.config.settings_for_command", return_value=_MOCK_SETTINGS):
        result = runner.invoke(_cmd.command, args or ["fisia", "MODEL123"])

    return result, mock_api_instance


def _invoke_http_error(status_code, args=None):
    """Invoke with fetch_data raising an HTTPError for the given status code."""
    runner = CliRunner()
    resp = MagicMock()
    resp.status_code = status_code
    http_error = requests.HTTPError(response=resp)

    mock_api_instance = MagicMock()
    mock_api_instance.fetch_data.side_effect = http_error
    mock_api_cls = MagicMock(return_value=mock_api_instance)

    with patch.object(_cmd, "TesseractAPI", mock_api_cls), \
         patch("common.config.settings_for_command", return_value=_MOCK_SETTINGS):
        result = runner.invoke(_cmd.command, args or ["fisia", "MODEL123"])

    return result


# ---------------------------------------------------------------------------
# TestCommand
# ---------------------------------------------------------------------------

class TestCommand:
    def test_exits_with_code_zero(self):
        result, _ = _invoke()
        assert result.exit_code == 0, result.output

    def test_calls_fetch_data_with_model(self):
        _, mock_api = _invoke(["fisia", "MYMODEL"])
        mock_api.fetch_data.assert_called_once_with("MYMODEL")

    def test_api_instantiated_with_fisia_bu(self):
        runner = CliRunner()
        mock_api_cls = MagicMock()
        mock_api_cls.return_value.fetch_data.return_value = {"modelVariations": []}
        with patch.object(_cmd, "TesseractAPI", mock_api_cls), \
             patch("common.config.settings_for_command", return_value=_MOCK_SETTINGS):
            runner.invoke(_cmd.command, ["fisia", "MODEL"])
        _, call_bu = mock_api_cls.call_args[0]
        assert call_bu == "fisia"

    def test_api_instantiated_with_centauro_bu(self):
        runner = CliRunner()
        mock_api_cls = MagicMock()
        mock_api_cls.return_value.fetch_data.return_value = {"modelVariations": []}
        with patch.object(_cmd, "TesseractAPI", mock_api_cls), \
             patch("common.config.settings_for_command", return_value=_MOCK_SETTINGS):
            runner.invoke(_cmd.command, ["centauro", "MODEL"])
        _, call_bu = mock_api_cls.call_args[0]
        assert call_bu == "centauro"

    def test_invalid_bu_argument_fails(self):
        result, _ = _invoke(["invalid_bu", "MODEL"])
        assert result.exit_code != 0

    # -----------------------------------------------------------------------
    # 404 HTTPError handling
    # -----------------------------------------------------------------------

    def test_404_prints_not_found_message(self):
        result = _invoke_http_error(404)
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_404_message_includes_model_name(self):
        result = _invoke_http_error(404, ["fisia", "MYMODEL"])
        assert "MYMODEL" in result.output

    def test_404_message_includes_bu(self):
        result = _invoke_http_error(404, ["fisia", "MYMODEL"])
        assert "fisia" in result.output

    def test_non_404_http_error_is_reraised(self):
        result = _invoke_http_error(500)
        assert result.exit_code != 0

    def test_403_http_error_is_reraised(self):
        result = _invoke_http_error(403)
        assert result.exit_code != 0

    # -----------------------------------------------------------------------
    # --show-only filter
    # -----------------------------------------------------------------------

    def test_show_only_all_shows_both_products(self):
        result, _ = _invoke(["fisia", "MODEL", "--show-only", "all"])
        assert "SKU001" in result.output
        assert "SKU002" in result.output

    def test_show_only_default_is_all(self):
        result, _ = _invoke(["fisia", "MODEL"])
        assert "SKU001" in result.output
        assert "SKU002" in result.output

    def test_show_only_blocked_shows_blocked_product(self):
        result, _ = _invoke(["fisia", "MODEL", "--show-only", "blocked"])
        assert "SKU002" in result.output

    def test_show_only_blocked_hides_unblocked_product(self):
        result, _ = _invoke(["fisia", "MODEL", "--show-only", "blocked"])
        assert "SKU001" not in result.output

    def test_show_only_unblocked_shows_unblocked_product(self):
        result, _ = _invoke(["fisia", "MODEL", "--show-only", "unblocked"])
        assert "SKU001" in result.output

    def test_show_only_unblocked_hides_blocked_product(self):
        result, _ = _invoke(["fisia", "MODEL", "--show-only", "unblocked"])
        assert "SKU002" not in result.output

    def test_show_only_invalid_choice_fails(self):
        result, _ = _invoke(["fisia", "MODEL", "--show-only", "invalid"])
        assert result.exit_code != 0

    # -----------------------------------------------------------------------
    # --quiet flag
    # -----------------------------------------------------------------------

    def test_quiet_suppresses_totals_line(self):
        result, _ = _invoke(["fisia", "MODEL", "--quiet"])
        assert "Total items" not in result.output

    def test_without_quiet_shows_totals_line(self):
        result, _ = _invoke(["fisia", "MODEL"])
        assert "Total items" in result.output

    def test_totals_reflect_all_and_matching_counts(self):
        result, _ = _invoke(["fisia", "MODEL", "--show-only", "blocked"])
        assert "Total items: 2" in result.output
        assert "Matching items: 1" in result.output

    def test_totals_all_items_when_no_filter(self):
        result, _ = _invoke(["fisia", "MODEL"])
        assert "Total items: 2" in result.output
        assert "Matching items: 2" in result.output

    # -----------------------------------------------------------------------
    # Output content
    # -----------------------------------------------------------------------

    def test_table_headers_present(self):
        result, _ = _invoke()
        for header in ["SKU", "EXTERNAL_ID", "BLOCKED", "AVAILABLE", "TOTAL", "BLOCK_REASONS"]:
            assert header in result.output

    def test_sku_appears_in_output(self):
        result, _ = _invoke()
        assert "SKU001" in result.output
        assert "SKU002" in result.output

    def test_external_id_appears_in_output(self):
        result, _ = _invoke()
        assert "EXT001" in result.output
        assert "EXT002" in result.output

    def test_block_reasons_joined_with_comma(self):
        result, _ = _invoke()
        assert "reason_a, reason_b" in result.output

    def test_stock_available_appears(self):
        result, _ = _invoke()
        assert "10" in result.output  # SKU001 available

    def test_stock_total_appears(self):
        result, _ = _invoke()
        assert "15" in result.output  # SKU001 total

    # -----------------------------------------------------------------------
    # Edge cases
    # -----------------------------------------------------------------------

    def test_empty_model_variations_exits_cleanly(self):
        result, _ = _invoke(fetch_data_return={"modelVariations": []})
        assert result.exit_code == 0

    def test_missing_model_variations_key_exits_cleanly(self):
        result, _ = _invoke(fetch_data_return={})
        assert result.exit_code == 0

    def test_empty_products_list_exits_cleanly(self):
        result, _ = _invoke(fetch_data_return={"modelVariations": [{"products": []}]})
        assert result.exit_code == 0

    def test_multiple_variations_all_products_counted(self):
        data = {
            "modelVariations": [
                {"products": [_PRODUCT_UNBLOCKED]},
                {"products": [_PRODUCT_BLOCKED]},
            ]
        }
        result, _ = _invoke(fetch_data_return=data)
        assert "Total items: 2" in result.output

    def test_product_with_empty_block_reasons_shows_empty_cell(self):
        data = {"modelVariations": [{"products": [_PRODUCT_UNBLOCKED]}]}
        result, _ = _invoke(fetch_data_return=data)
        assert result.exit_code == 0
        assert "SKU001" in result.output

    def test_product_missing_stock_key_does_not_crash(self):
        product = {"sku": "NOSTOCK", "externalId": "E", "blocked": False, "blockReasons": []}
        result, _ = _invoke(fetch_data_return={"modelVariations": [{"products": [product]}]})
        assert result.exit_code == 0
        assert "NOSTOCK" in result.output
