import json
import time

DEFAULT_CACHE_DIR = ".cache"

class Cache:
    """A simple file-based cache with optional TTL support, namespaced by command."""

    def __init__(self, namespace:str):
        self._validate_namespace(namespace)
        self.namespace = namespace
        self.cache_file = f"{DEFAULT_CACHE_DIR}/{namespace}.json"
        self.data = self.load()

    def load(self) -> dict:
        """Load the cache from disk, returning an empty dict if the file doesn't exist."""
        try:
            with open(self.cache_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save(self) -> None:
        """Save the current cache data to disk."""
        with open(self.cache_file, "w") as f:
            json.dump(self.data, f)

    def get(self, key: str, default=None, ignore_expiry: bool = False):
        """Get a value from the cache, returning default if not found."""
        cache = self.data.get(key)
        if not cache:
            return default

        expires_at = cache.get("expires_at")
        if not ignore_expiry and expires_at and expires_at < time.time():
            return default

        return cache.get("value")

    def set(self, key: str, value, ttl: int | None = None) -> None:
        """Set a value in the cache, optionally with a TTL in seconds."""
        expires_at = time.time() + ttl if ttl is not None else None
        self.data[key] = {"value": value, "expires_at": expires_at}
        self.save()

    def _validate_namespace(self, namespace: str) -> None:
        """Validate that the namespace is a valid filename."""
        if not namespace.isidentifier():
            raise ValueError(f"Invalid namespace '{namespace}'. Must be a valid identifier.")
