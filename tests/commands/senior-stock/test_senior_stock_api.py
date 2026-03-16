"""
tests/commands/senior-stock/test_senior_stock_api.py
Unit tests for commands/senior-stock/senior_stock_api.py

Covers:
  - _validate_settings — all required keys, wrong type
  - __init__ — attribute assignment from settings
  - authenticate — cache hit, cache miss (HTTP success), force_refresh, HTTP error
  - get_all_stock — cache hit, cache miss (happy path), no_cache flag,
                    401 retry logic (success on retry, max-retries exceeded),
                    non-401 HTTP error re-raised
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

# ---------------------------------------------------------------------------
# Make the commands/senior-stock package importable without installing it.
# The directory name contains a hyphen so it cannot be a Python package name;
# we register it as a module alias.
# ---------------------------------------------------------------------------
_SENIOR_STOCK_DIR = str(
    Path(__file__).parent.parent.parent.parent / "commands" / "senior-stock"
)
if _SENIOR_STOCK_DIR not in sys.path:
    sys.path.insert(0, _SENIOR_STOCK_DIR)

from senior_stock_api import (  # noqa: E402
    SeniorStockAPI,
    CACHE_KEY_TOKEN,
    CACHE_KEY_DATA,
    CACHE_TOKEN_TTL_SECONDS,
    CACHE_DATA_TTL_SECONDS,
    MAX_RETRIES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_SETTINGS = {
    "stock_url": "https://api.example.com/stock",
    "auth_url": "https://api.example.com/auth",
    "cd_empresa": "001",
    "cd_deposito": "01",
    "tp_consulta": "T",
    "id_produto_sem_estoque": "S",
    "usuario": "user",
    "senha": "secret",
}


@pytest.fixture()
def mock_cache():
    cache = MagicMock()
    cache.get.return_value = None  # cold cache by default
    return cache


@pytest.fixture()
def api(mock_cache):
    return SeniorStockAPI(VALID_SETTINGS.copy(), mock_cache)


def _make_response(status_code: int = 200, text: str = "", json_data=None):
    """Build a minimal requests.Response-like mock."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        http_err = requests.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_err
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# _validate_settings
# ---------------------------------------------------------------------------

class TestValidateSettings:
    def test_accepts_valid_settings(self):
        SeniorStockAPI(VALID_SETTINGS.copy(), MagicMock())  # must not raise

    def test_raises_when_settings_not_a_dict(self):
        with pytest.raises(ValueError, match="must be a dictionary"):
            SeniorStockAPI("not-a-dict", MagicMock())

    @pytest.mark.parametrize("missing_key", list(VALID_SETTINGS.keys()))
    def test_raises_when_required_key_missing(self, missing_key):
        settings = VALID_SETTINGS.copy()
        del settings[missing_key]
        with pytest.raises(ValueError, match=missing_key):
            SeniorStockAPI(settings, MagicMock())


# ---------------------------------------------------------------------------
# __init__ attribute assignment
# ---------------------------------------------------------------------------

class TestInit:
    def test_attributes_are_set_from_settings(self, mock_cache):
        a = SeniorStockAPI(VALID_SETTINGS.copy(), mock_cache)
        assert a.stock_url == VALID_SETTINGS["stock_url"]
        assert a.auth_url == VALID_SETTINGS["auth_url"]
        assert a.cd_empresa == VALID_SETTINGS["cd_empresa"]
        assert a.cd_deposito == VALID_SETTINGS["cd_deposito"]
        assert a.tp_consulta == VALID_SETTINGS["tp_consulta"]
        assert a.id_produto_sem_estoque == VALID_SETTINGS["id_produto_sem_estoque"]
        assert a.usuario == VALID_SETTINGS["usuario"]
        assert a.senha == VALID_SETTINGS["senha"]

    def test_cache_is_stored(self, mock_cache):
        a = SeniorStockAPI(VALID_SETTINGS.copy(), mock_cache)
        assert a.cache is mock_cache


# ---------------------------------------------------------------------------
# authenticate
# ---------------------------------------------------------------------------

class TestAuthenticate:
    def test_returns_cached_token_without_http_call(self, api, mock_cache):
        mock_cache.get.return_value = "cached-token"
        with patch("requests.post") as mock_post:
            token = api.authenticate()
        assert token == "cached-token"
        mock_post.assert_not_called()

    def test_fetches_token_when_cache_empty(self, api, mock_cache):
        mock_cache.get.return_value = None
        resp = _make_response(200, text="new-token")
        with patch("requests.post", return_value=resp) as mock_post:
            token = api.authenticate()
        assert token == "new-token"
        mock_post.assert_called_once_with(
            VALID_SETTINGS["auth_url"],
            json={"usuario": VALID_SETTINGS["usuario"], "senha": VALID_SETTINGS["senha"]},
        )

    def test_caches_token_after_fetch(self, api, mock_cache):
        mock_cache.get.return_value = None
        resp = _make_response(200, text="tok")
        with patch("requests.post", return_value=resp):
            api.authenticate()
        mock_cache.set.assert_called_once_with(
            CACHE_KEY_TOKEN, "tok", ttl=CACHE_TOKEN_TTL_SECONDS
        )

    def test_force_refresh_bypasses_cache(self, api, mock_cache):
        mock_cache.get.return_value = "old-token"
        resp = _make_response(200, text="refreshed-token")
        with patch("requests.post", return_value=resp):
            token = api.authenticate(force_refresh=True)
        assert token == "refreshed-token"

    def test_raises_on_http_error(self, api, mock_cache):
        mock_cache.get.return_value = None
        resp = _make_response(500)
        with patch("requests.post", return_value=resp):
            with pytest.raises(requests.HTTPError):
                api.authenticate()


# ---------------------------------------------------------------------------
# get_all_stock
# ---------------------------------------------------------------------------

class TestGetAllStock:
    def test_returns_cached_data_without_http_call(self, api, mock_cache):
        cached = {"items": [1, 2]}
        mock_cache.get.return_value = cached
        with patch("requests.post") as mock_post:
            result = api.get_all_stock()
        assert result == cached
        mock_post.assert_not_called()

    def test_no_cache_flag_bypasses_cache(self, api, mock_cache):
        cached = {"items": [1]}
        stock_data = {"items": [2]}

        # First call to cache.get returns the cached token for authenticate(),
        # second call (for stock data inside get_all_stock) simulates cache hit
        # that should be bypassed.
        mock_cache.get.side_effect = ["token", cached]

        resp = _make_response(200, json_data=stock_data)
        with patch("requests.post", return_value=resp):
            result = api.get_all_stock(no_cache=True)
        assert result == stock_data

    def test_fetches_and_caches_stock_data(self, api, mock_cache):
        stock_data = {"items": [{"sku": "A", "qty": 10}]}
        mock_cache.get.side_effect = [None, None]  # no cached data, no cached token

        auth_resp = _make_response(200, text="bearer-token")
        stock_resp = _make_response(200, json_data=stock_data)

        with patch("requests.post", side_effect=[auth_resp, stock_resp]):
            result = api.get_all_stock()

        assert result == stock_data
        mock_cache.set.assert_any_call(CACHE_KEY_DATA, stock_data, ttl=CACHE_DATA_TTL_SECONDS)

    def test_sends_correct_headers_and_body(self, api, mock_cache):
        # First cache.get call is for CACHE_KEY_DATA (miss → continue).
        # Second cache.get call is inside authenticate() for CACHE_KEY_TOKEN (hit → skip HTTP).
        mock_cache.get.side_effect = [None, "bearer-token"]
        stock_resp = _make_response(200, json_data={})

        with patch("requests.post", return_value=stock_resp) as mock_post:
            api.get_all_stock()

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer bearer-token"
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert kwargs["json"]["cd_empresa"] == VALID_SETTINGS["cd_empresa"]
        assert kwargs["json"]["cd_deposito"] == VALID_SETTINGS["cd_deposito"]
        assert kwargs["json"]["tp_consulta"] == VALID_SETTINGS["tp_consulta"]
        assert kwargs["json"]["id_produto_sem_estoque"] == VALID_SETTINGS["id_produto_sem_estoque"]

    def test_retries_on_401_with_token_refresh(self, api, mock_cache):
        """A 401 should trigger a token refresh and one retry."""
        stock_data = {"items": []}
        # cache.get call sequence (authenticate always calls cache.get even with force_refresh):
        #   1. CACHE_KEY_DATA in get_all_stock (first call)              → None
        #   2. CACHE_KEY_TOKEN in authenticate()                         → None → HTTP auth_resp_1
        #   3. CACHE_KEY_TOKEN in authenticate(force_refresh=True)       → None → HTTP auth_resp_2
        #   4. CACHE_KEY_DATA in get_all_stock (recursive call)          → None
        #   5. CACHE_KEY_TOKEN in authenticate() (recursive, no refresh) → "token-2" → skip HTTP
        # requests.post calls: auth_resp_1, unauthorized, auth_resp_2, stock_resp_ok
        mock_cache.get.side_effect = [None, None, None, None, "token-2"]

        auth_resp_1 = _make_response(200, text="token-1")
        unauthorized = _make_response(401)
        auth_resp_2 = _make_response(200, text="token-2")
        stock_resp_ok = _make_response(200, json_data=stock_data)

        with patch(
            "requests.post",
            side_effect=[auth_resp_1, unauthorized, auth_resp_2, stock_resp_ok],
        ):
            result = api.get_all_stock()

        assert result == stock_data

    def test_raises_after_max_retries_on_401(self, api, mock_cache):
        """After MAX_RETRIES 401s the method must raise an Exception."""
        mock_cache.get.return_value = None

        # auth + 401 repeated MAX_RETRIES+1 times
        side_effects = []
        for _ in range(MAX_RETRIES + 1):
            side_effects.append(_make_response(200, text=f"token"))
            side_effects.append(_make_response(401))

        with patch("requests.post", side_effect=side_effects):
            with pytest.raises(Exception, match="Maximum retry attempts reached"):
                api.get_all_stock()

    def test_reraises_non_401_http_error(self, api, mock_cache):
        """HTTP errors other than 401 must propagate unchanged."""
        mock_cache.get.side_effect = [None, None]

        auth_resp = _make_response(200, text="token")
        server_error = _make_response(500)

        with patch("requests.post", side_effect=[auth_resp, server_error]):
            with pytest.raises(requests.HTTPError):
                api.get_all_stock()
