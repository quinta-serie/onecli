"""
tests/test_cache.py — Unit tests for common.cache.Cache.

Covers:
  - Namespace validation (__init__ / _validate_namespace)
  - Loading cache data from disk (load)
  - Persisting cache data to disk (save)
  - Reading values with and without TTL (get)
  - Writing values with and without TTL (set)

All tests are isolated from the real filesystem via the ``tmp_path`` fixture
and monkeypatching of ``common.cache.DEFAULT_CACHE_DIR``.
"""

import json
import time

import pytest

from common.cache import Cache


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def cache_dir(tmp_path, monkeypatch):
    """
    Patch DEFAULT_CACHE_DIR to a pytest-managed temp directory and return
    a factory that produces Cache instances inside that directory.
    """
    monkeypatch.setattr("common.cache.DEFAULT_CACHE_DIR", str(tmp_path))

    def _make(namespace: str = "testns") -> Cache:
        return Cache(namespace)

    _make.path = tmp_path
    return _make


# ---------------------------------------------------------------------------
# __init__ / general construction
# ---------------------------------------------------------------------------


class TestCacheInit:
    def test_namespace_is_stored(self, cache_dir):
        c = cache_dir("myns")
        assert c.namespace == "myns"

    def test_cache_file_path_uses_namespace(self, cache_dir):
        c = cache_dir("myns")
        assert c.cache_file == f"{cache_dir.path}/myns.json"

    def test_data_is_empty_dict_when_no_file_exists(self, cache_dir):
        c = cache_dir()
        assert c.data == {}

    def test_data_is_preloaded_from_existing_file(self, cache_dir):
        payload = {"k": {"value": "v", "expires_at": None}}
        (cache_dir.path / "testns.json").write_text(json.dumps(payload))
        c = cache_dir()
        assert c.data == payload

    def test_different_namespaces_use_different_files(self, cache_dir):
        a = cache_dir("alpha")
        b = cache_dir("beta")
        assert a.cache_file != b.cache_file


# ---------------------------------------------------------------------------
# _validate_namespace
# ---------------------------------------------------------------------------


class TestValidateNamespace:
    def test_simple_name_accepted(self, cache_dir):
        cache_dir("abc")  # must not raise

    def test_underscore_prefix_accepted(self, cache_dir):
        cache_dir("_private")  # must not raise

    def test_name_with_digits_accepted(self, cache_dir):
        cache_dir("cache1")  # must not raise

    def test_hyphen_rejected(self, cache_dir):
        with pytest.raises(ValueError, match="Invalid namespace"):
            cache_dir("my-cache")

    def test_space_rejected(self, cache_dir):
        with pytest.raises(ValueError, match="Invalid namespace"):
            cache_dir("my cache")

    def test_leading_digit_rejected(self, cache_dir):
        with pytest.raises(ValueError, match="Invalid namespace"):
            cache_dir("1cache")

    def test_empty_string_rejected(self, cache_dir):
        with pytest.raises(ValueError, match="Invalid namespace"):
            cache_dir("")

    def test_dot_notation_rejected(self, cache_dir):
        with pytest.raises(ValueError, match="Invalid namespace"):
            cache_dir("my.cache")


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------


class TestLoad:
    def test_returns_empty_dict_when_file_missing(self, cache_dir):
        c = cache_dir()
        assert c.load() == {}

    def test_returns_data_when_file_exists(self, cache_dir):
        payload = {"foo": {"value": 42, "expires_at": None}}
        (cache_dir.path / "testns.json").write_text(json.dumps(payload))
        c = cache_dir()
        assert c.load() == payload

    def test_load_reflects_external_file_changes(self, cache_dir):
        c = cache_dir()
        assert c.load() == {}
        new_payload = {"bar": {"value": "baz", "expires_at": None}}
        (cache_dir.path / "testns.json").write_text(json.dumps(new_payload))
        assert c.load() == new_payload


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------


class TestSave:
    def test_save_writes_data_as_json(self, cache_dir):
        c = cache_dir()
        c.data = {"key": {"value": "hello", "expires_at": None}}
        c.save()
        written = json.loads((cache_dir.path / "testns.json").read_text())
        assert written == c.data

    def test_save_overwrites_previous_content(self, cache_dir):
        c = cache_dir()
        c.data = {"old": {"value": "data", "expires_at": None}}
        c.save()
        c.data = {"new": {"value": "data", "expires_at": None}}
        c.save()
        written = json.loads((cache_dir.path / "testns.json").read_text())
        assert "new" in written
        assert "old" not in written

    def test_save_and_load_roundtrip(self, cache_dir):
        c = cache_dir()
        c.data = {"x": {"value": [1, 2, 3], "expires_at": None}}
        c.save()
        assert c.load() == c.data


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestGet:
    def test_returns_none_for_missing_key_by_default(self, cache_dir):
        c = cache_dir()
        assert c.get("missing") is None

    def test_returns_custom_default_for_missing_key(self, cache_dir):
        c = cache_dir()
        assert c.get("missing", "fallback") == "fallback"

    def test_returns_value_for_key_without_ttl(self, cache_dir):
        c = cache_dir()
        c.data = {"k": {"value": "hello", "expires_at": None}}
        assert c.get("k") == "hello"

    def test_returns_value_for_non_expired_key(self, cache_dir):
        c = cache_dir()
        c.data = {"k": {"value": "fresh", "expires_at": time.time() + 3600}}
        assert c.get("k") == "fresh"

    def test_returns_default_for_expired_key(self, cache_dir):
        c = cache_dir()
        c.data = {"k": {"value": "stale", "expires_at": time.time() - 1}}
        assert c.get("k") is None

    def test_returns_custom_default_for_expired_key(self, cache_dir):
        c = cache_dir()
        c.data = {"k": {"value": "stale", "expires_at": time.time() - 1}}
        assert c.get("k", "fallback") == "fallback"

    def test_ignore_expiry_returns_value_for_expired_key(self, cache_dir):
        c = cache_dir()
        c.data = {"k": {"value": "stale", "expires_at": time.time() - 1}}
        assert c.get("k", ignore_expiry=True) == "stale"

    def test_ignore_expiry_returns_value_for_non_expired_key(self, cache_dir):
        c = cache_dir()
        c.data = {"k": {"value": "fresh", "expires_at": time.time() + 3600}}
        assert c.get("k", ignore_expiry=True) == "fresh"

    def test_ignore_expiry_returns_value_for_key_without_ttl(self, cache_dir):
        c = cache_dir()
        c.data = {"k": {"value": "eternal", "expires_at": None}}
        assert c.get("k", ignore_expiry=True) == "eternal"

    def test_ignore_expiry_false_still_enforces_expiry(self, cache_dir):
        c = cache_dir()
        c.data = {"k": {"value": "stale", "expires_at": time.time() - 1}}
        assert c.get("k", ignore_expiry=False) is None

    def test_returns_none_value_stored_against_a_key(self, cache_dir):
        # set() always stores a dict with two keys, which is truthy,
        # so None as the stored value is still retrievable.
        c = cache_dir()
        c.set("k", None)
        assert c.get("k") is None
        # Disambiguate from "key missing" by checking the key exists in data.
        assert "k" in c.data


# ---------------------------------------------------------------------------
# set
# ---------------------------------------------------------------------------


class TestSet:
    def test_set_stores_value(self, cache_dir):
        c = cache_dir()
        c.set("k", "value")
        assert c.data["k"]["value"] == "value"

    def test_set_without_ttl_stores_none_expires_at(self, cache_dir):
        c = cache_dir()
        c.set("k", "value")
        assert c.data["k"]["expires_at"] is None

    def test_set_with_ttl_stores_future_timestamp(self, cache_dir):
        c = cache_dir()
        before = time.time()
        c.set("k", "value", ttl=60)
        after = time.time()
        expires_at = c.data["k"]["expires_at"]
        assert before + 60 <= expires_at <= after + 60

    def test_set_persists_to_disk(self, cache_dir):
        c = cache_dir()
        c.set("k", "persisted")
        written = json.loads((cache_dir.path / "testns.json").read_text())
        assert written["k"]["value"] == "persisted"

    def test_set_overwrites_existing_key(self, cache_dir):
        c = cache_dir()
        c.set("k", "first")
        c.set("k", "second")
        assert c.get("k") == "second"

    def test_set_multiple_keys_independently(self, cache_dir):
        c = cache_dir()
        c.set("a", 1)
        c.set("b", 2)
        assert c.get("a") == 1
        assert c.get("b") == 2

    def test_set_accepts_complex_values(self, cache_dir):
        c = cache_dir()
        payload = {"nested": [1, 2, {"deep": True}]}
        c.set("k", payload)
        assert c.get("k") == payload
