"""
tests/commands/tesseract/test_tesseract_api.py
Unit tests for commands/tesseract/tesseract_api.py

Covers:
  - _validate_settings  — missing/present combinations of required URL keys
  - _get_url_by_business_unit — fisia, centauro, unsupported BU
  - __init__            — correct URL stored, invalid settings raises
  - fetch_data          — correct URL construction, raise_for_status called,
                          JSON returned, HTTPError propagated
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

# ---------------------------------------------------------------------------
# Make commands/tesseract importable directly (no relative imports in this file)
# ---------------------------------------------------------------------------
_TESSERACT_DIR = str(
    Path(__file__).parent.parent.parent.parent / "commands" / "tesseract"
)
if _TESSERACT_DIR not in sys.path:
    sys.path.insert(0, _TESSERACT_DIR)

from tesseract_api import TesseractAPI  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FISIA_URL    = "https://fisia.example.com/api/"
CENTAURO_URL = "https://centauro.example.com/api/"

FISIA_SETTINGS    = {"tesseract_fisia_url": FISIA_URL}
CENTAURO_SETTINGS = {"tesseract_centauro_url": CENTAURO_URL}
BOTH_SETTINGS     = {"tesseract_fisia_url": FISIA_URL, "tesseract_centauro_url": CENTAURO_URL}


def _make_response(status_code=200, json_data=None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        http_error = requests.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_error
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# _validate_settings
# ---------------------------------------------------------------------------

class TestValidateSettings:
    def _api_with(self, settings, bu="fisia"):
        return TesseractAPI(settings, bu)

    def test_raises_when_both_urls_missing(self):
        with pytest.raises(ValueError, match="Missing required setting"):
            TesseractAPI({}, "fisia")

    def test_raises_when_unrelated_keys_only(self):
        with pytest.raises(ValueError):
            TesseractAPI({"other_key": "value"}, "fisia")

    def test_passes_with_only_fisia_url(self):
        api = TesseractAPI(FISIA_SETTINGS, "fisia")
        assert api is not None

    def test_passes_with_only_centauro_url(self):
        api = TesseractAPI(CENTAURO_SETTINGS, "centauro")
        assert api is not None

    def test_passes_with_both_urls(self):
        api = TesseractAPI(BOTH_SETTINGS, "fisia")
        assert api is not None


# ---------------------------------------------------------------------------
# _get_url_by_business_unit
# ---------------------------------------------------------------------------

class TestGetUrlByBusinessUnit:
    def test_fisia_returns_fisia_url(self):
        api = TesseractAPI(BOTH_SETTINGS, "fisia")
        assert api.tesseract_url == FISIA_URL

    def test_centauro_returns_centauro_url(self):
        api = TesseractAPI(BOTH_SETTINGS, "centauro")
        assert api.tesseract_url == CENTAURO_URL

    def test_unsupported_bu_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported business unit"):
            TesseractAPI(BOTH_SETTINGS, "unknown")

    def test_fisia_url_from_settings_key(self):
        settings = {"tesseract_fisia_url": "https://custom-fisia.com/", "tesseract_centauro_url": "x"}
        api = TesseractAPI(settings, "fisia")
        assert api.tesseract_url == "https://custom-fisia.com/"

    def test_centauro_url_from_settings_key(self):
        settings = {"tesseract_fisia_url": "x", "tesseract_centauro_url": "https://custom-centauro.com/"}
        api = TesseractAPI(settings, "centauro")
        assert api.tesseract_url == "https://custom-centauro.com/"


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_stores_fisia_url(self):
        api = TesseractAPI(FISIA_SETTINGS, "fisia")
        assert api.tesseract_url == FISIA_URL

    def test_stores_centauro_url(self):
        api = TesseractAPI(CENTAURO_SETTINGS, "centauro")
        assert api.tesseract_url == CENTAURO_URL

    def test_invalid_settings_raises_before_url_lookup(self):
        with pytest.raises(ValueError):
            TesseractAPI({}, "fisia")


# ---------------------------------------------------------------------------
# fetch_data
# ---------------------------------------------------------------------------

class TestFetchData:
    def _api(self, bu="fisia"):
        return TesseractAPI(BOTH_SETTINGS, bu)

    def test_get_called_with_joined_url(self):
        api = self._api()
        resp = _make_response(200, {"modelVariations": []})
        with patch("requests.get", return_value=resp) as mock_get:
            api.fetch_data("MODEL123")
        mock_get.assert_called_once()
        url_used = mock_get.call_args[0][0]
        assert "MODEL123" in url_used
        assert FISIA_URL.rstrip("/") in url_used

    def test_raise_for_status_called(self):
        api = self._api()
        resp = _make_response(200, {})
        with patch("requests.get", return_value=resp):
            api.fetch_data("X")
        resp.raise_for_status.assert_called_once()

    def test_returns_parsed_json(self):
        api = self._api()
        payload = {"modelVariations": [{"products": []}]}
        resp = _make_response(200, payload)
        with patch("requests.get", return_value=resp):
            result = api.fetch_data("X")
        assert result == payload

    def test_404_raises_http_error(self):
        api = self._api()
        resp = _make_response(404)
        with patch("requests.get", return_value=resp):
            with pytest.raises(requests.HTTPError):
                api.fetch_data("X")

    def test_500_raises_http_error(self):
        api = self._api()
        resp = _make_response(500)
        with patch("requests.get", return_value=resp):
            with pytest.raises(requests.HTTPError):
                api.fetch_data("X")

    def test_url_joined_correctly_for_centauro(self):
        api = self._api("centauro")
        resp = _make_response(200, {})
        with patch("requests.get", return_value=resp) as mock_get:
            api.fetch_data("MYMODEL")
        url_used = mock_get.call_args[0][0]
        assert CENTAURO_URL.rstrip("/") in url_used
        assert "MYMODEL" in url_used
