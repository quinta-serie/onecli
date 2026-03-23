"""
tests/commands/senior-stock/test_command.py
Unit tests for commands/senior-stock/__init__.py

Covers:
  - parse_filters  — empty input, exact match, regex match, mixed, malformed
  - parse_columns  — no columns arg, explicit columns, all_columns_flag, flag overrides arg
  - command (CLI)  — happy path output, --filter exact, --filter regex,
                     --columns, --all-columns, --no-cache, no matching rows
"""

import re
import sys
import types
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

_SENIOR_STOCK_DIR = str(
    Path(__file__).parent.parent.parent.parent / "commands" / "senior-stock"
)
_PKG_NAME = "senior_stock_cmd"

_MOCK_SETTINGS = {
    "stock_url": "https://api.example.com/stock",
    "auth_url": "https://api.example.com/auth",
    "cd_empresa": "001",
    "cd_deposito": "01",
    "tp_consulta": "T",
    "id_produto_sem_estoque": "S",
    "usuario": "user",
    "senha": "secret",
}

_STOCK_ROWS = [
    {
        "cd_empresa": "001",
        "cd_produto": "P001",
        "ds_produto": "Product One",
        "nu_lote": "L01",
        "qt_disponivel": "10",
        "qt_reservado": "2",
        "qt_reservado_digital": "0",
        "ean": "1111111111111",
        "tem_estoque": "S",
        "ds_area_erp": "ERP",
        "cd_area_armaz": "A1",
        "ds_area_armaz": "Area 1",
        "id_area_faturavel": "S",
        "id_resultado_completo": "S",
    },
    {
        "cd_empresa": "001",
        "cd_produto": "P002",
        "ds_produto": "Product Two",
        "nu_lote": "L02",
        "qt_disponivel": "0",
        "qt_reservado": "0",
        "qt_reservado_digital": "0",
        "ean": "2222222222222",
        "tem_estoque": "N",
        "ds_area_erp": "ERP",
        "cd_area_armaz": "A2",
        "ds_area_armaz": "Area 2",
        "id_area_faturavel": "S",
        "id_resultado_completo": "S",
    },
]


# ---------------------------------------------------------------------------
# Module loader
# ---------------------------------------------------------------------------

def _load_cmd_module():
    """
    Load commands/senior-stock/__init__.py as a proper Python package so
    that the relative import ``from .senior_stock_api import SeniorStockAPI``
    resolves correctly.

    Steps
    -----
    1. Register a package stub ``senior_stock_cmd`` in sys.modules with its
       __path__ pointing to the senior-stock directory.
    2. Load senior_stock_api.py as ``senior_stock_cmd.senior_stock_api`` and
       register it so the relative import finds it.
    3. Execute __init__.py into the stub module.
    """
    # Clean up any previously loaded version
    for key in list(sys.modules):
        if key == _PKG_NAME or key.startswith(_PKG_NAME + "."):
            del sys.modules[key]

    # 1. Package stub
    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [_SENIOR_STOCK_DIR]
    pkg.__package__ = _PKG_NAME
    pkg.__name__ = _PKG_NAME
    sys.modules[_PKG_NAME] = pkg

    # 2. Load senior_stock_api.py as submodule
    api_spec = importlib.util.spec_from_file_location(
        f"{_PKG_NAME}.senior_stock_api",
        Path(_SENIOR_STOCK_DIR) / "senior_stock_api.py",
    )
    api_mod = importlib.util.module_from_spec(api_spec)
    api_mod.__package__ = _PKG_NAME
    sys.modules[f"{_PKG_NAME}.senior_stock_api"] = api_mod
    api_spec.loader.exec_module(api_mod)

    # 3. Execute __init__.py into the pkg stub
    init_spec = importlib.util.spec_from_file_location(
        _PKG_NAME,
        Path(_SENIOR_STOCK_DIR) / "__init__.py",
        submodule_search_locations=[_SENIOR_STOCK_DIR],
    )
    with patch("common.config.settings_for_command", return_value=_MOCK_SETTINGS):
        init_spec.loader.exec_module(pkg)

    return pkg


# Load once at module import time; individual tests patch as needed
_cmd = _load_cmd_module()


# ---------------------------------------------------------------------------
# filter expressions (delegated to FilterEngine — parse_filters removed)
# ---------------------------------------------------------------------------

class TestFilterExpressions:
    """Verify filter expressions are correctly passed through to FilterEngine."""

    def test_no_filter_returns_all_rows(self):
        result, _ = _invoke()
        assert "P001" in result.output
        assert "P002" in result.output

    def test_eq_filter_keeps_matching_row(self):
        result, _ = _invoke(["--filter", "ean[eq]1111111111111"])
        assert "P001" in result.output
        assert "P002" not in result.output

    def test_eq_filter_no_match_returns_empty_table(self):
        result, _ = _invoke(["--filter", "ean[eq]9999999999999"])
        assert "P001" not in result.output
        assert "P002" not in result.output

    def test_re_filter_keeps_matching_row(self):
        result, _ = _invoke(["--filter", "ean[re]^111"])
        assert "P001" in result.output
        assert "P002" not in result.output

    def test_ne_filter_excludes_row(self):
        result, _ = _invoke(["--filter", "ean[ne]1111111111111"])
        assert "P002" in result.output
        assert "P001" not in result.output

    def test_contains_filter(self):
        result, _ = _invoke(["--filter", "ds_produto[contains]One",
                              "--columns", "cd_produto,ds_produto"])
        assert "P001" in result.output
        assert "P002" not in result.output

    def test_unknown_separator_produces_no_filtering(self):
        # Unrecognized separator → FilterEngine ignores it → all rows shown
        result, _ = _invoke(["--filter", "ean~1111111111111"])
        assert "P001" in result.output
        assert "P002" in result.output

    def test_multiple_filter_flags_applied(self):
        result, _ = _invoke(["--filter", "ean[eq]1111111111111",
                              "--filter", "cd_produto[eq]P001"])
        assert "P001" in result.output
        assert "P002" not in result.output


# ---------------------------------------------------------------------------
# parse_columns
# ---------------------------------------------------------------------------

class TestParseColumns:
    def test_no_columns_returns_default(self):
        assert _cmd.parse_columns(None, False) == _cmd.DEFAULT_COLUMNS

    def test_explicit_columns_parsed(self):
        assert _cmd.parse_columns("ean,cd_produto", False) == ["ean", "cd_produto"]

    def test_all_columns_flag_returns_all(self):
        assert _cmd.parse_columns(None, True) == _cmd.DEFAULT_ALL_COLUMNS

    def test_all_columns_flag_overrides_explicit_columns(self):
        assert _cmd.parse_columns("ean", True) == _cmd.DEFAULT_ALL_COLUMNS

    def test_single_column(self):
        assert _cmd.parse_columns("ean", False) == ["ean"]

    def test_default_columns_contains_expected_fields(self):
        assert "cd_produto" in _cmd.DEFAULT_COLUMNS
        assert "ean" in _cmd.DEFAULT_COLUMNS
        assert "qt_disponivel" in _cmd.DEFAULT_COLUMNS


# ---------------------------------------------------------------------------
# command (CLI integration via CliRunner)
# ---------------------------------------------------------------------------

def _invoke(args=None, stock_data=None):
    """Invoke the CLI command with fully mocked I/O dependencies."""
    runner = CliRunner()
    data = stock_data if stock_data is not None else _STOCK_ROWS

    mock_api_instance = MagicMock()
    mock_api_instance.get_all_stock.return_value = data
    mock_api_cls = MagicMock(return_value=mock_api_instance)
    mock_cache = MagicMock()

    with patch.object(_cmd, "SeniorStockAPI", mock_api_cls), \
         patch.object(_cmd, "Cache", return_value=mock_cache), \
         patch("common.config.settings_for_command", return_value=_MOCK_SETTINGS):
        result = runner.invoke(_cmd.command, args or [])

    return result, mock_api_instance


class TestCommand:
    def test_exits_with_code_zero(self):
        result, _ = _invoke()
        assert result.exit_code == 0, result.output

    def test_calls_get_all_stock(self):
        _, mock_api = _invoke()
        mock_api.get_all_stock.assert_called_once()

    def test_no_cache_flag_passed_to_api(self):
        _, mock_api = _invoke(["--no-cache"])
        mock_api.get_all_stock.assert_called_once_with(no_cache=True)

    def test_default_no_cache_is_false(self):
        _, mock_api = _invoke()
        mock_api.get_all_stock.assert_called_once_with(no_cache=False)

    def test_exact_filter_keeps_matching_rows(self):
        result, _ = _invoke(["--filter", "ean[eq]1111111111111"])
        assert result.exit_code == 0, result.output
        assert "P001" in result.output
        assert "P002" not in result.output

    def test_exact_filter_drops_non_matching_rows(self):
        result, _ = _invoke(["--filter", "ean[eq]9999999999999"])
        assert "P001" not in result.output
        assert "P002" not in result.output

    def test_regex_filter_keeps_matching_rows(self):
        result, _ = _invoke(["--filter", "ean[re]^111"])
        assert result.exit_code == 0, result.output
        assert "P001" in result.output
        assert "P002" not in result.output

    def test_multiple_filters_are_cumulative(self):
        result, _ = _invoke([
            "--filter", "ean[eq]1111111111111",
            "--filter", "cd_produto[eq]P001",
        ])
        assert "P001" in result.output
        assert "P002" not in result.output

    def test_custom_columns_appear_in_output(self):
        result, _ = _invoke(["--columns", "cd_produto,ean"])
        assert result.exit_code == 0, result.output
        assert "cd_produto" in result.output
        assert "ean" in result.output

    def test_all_columns_flag_shows_all_headers(self):
        result, _ = _invoke(["--all-columns"])
        assert result.exit_code == 0, result.output
        # --all-columns includes cd_area_armaz (values A1/A2) which are absent
        # from the default 3-column view, confirming extra columns are rendered.
        assert "A1" in result.output
        assert "A2" in result.output

    def test_no_matching_rows_produces_no_row_data(self):
        result, _ = _invoke(["--filter", "ean[eq]000"])
        assert result.exit_code == 0
        assert "P001" not in result.output
        assert "P002" not in result.output

    def test_empty_stock_data_exits_cleanly(self):
        result, _ = _invoke(stock_data=[])
        assert result.exit_code == 0

    def test_both_rows_appear_with_no_filter(self):
        result, _ = _invoke()
        assert "P001" in result.output
        assert "P002" in result.output


# ---------------------------------------------------------------------------
