"""
Lightweight JSON-based cache utility with expiration support.
"""

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from ryutils import log
from ryutils.verbose import Verbose


class JsonCache:
    """
    A lightweight JSON-based cache with expiration support.

    Cache entries are stored with timestamps and automatically expired
    based on the configured expiry time. This class is thread-safe.
    """

    def __init__(
        self,
        cache_file: Path,
        expiry_seconds: int = 3600,  # 1 hour default
        verbose: Verbose = Verbose(),
    ) -> None:
        """
        Initialize the cache.

        Args:
            cache_file: Path to the JSON cache file
            expiry_seconds: Cache expiry time in seconds
            verbose: Verbose logging configuration
        """
        self.cache_file = cache_file
        self.expiry_seconds = expiry_seconds
        self.verbose = verbose
        self._cache_data: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache data from file and clean expired entries."""
        with self._lock:
            if not self.cache_file.exists():
                self._cache_data = {}
                return

            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache_data = json.load(f)

                # Clean expired entries
                self._clean_expired_entries()

                if self.verbose.request_cache:
                    log.print_normal(
                        f"Loaded cache from {self.cache_file} with {len(self._cache_data)} entries"
                    )

            except (json.JSONDecodeError, OSError) as e:
                log.print_warn(f"Error loading cache from {self.cache_file}: {e}")
                self._cache_data = {}

    def _save_cache(self) -> None:
        """Save cache data to file."""
        with self._lock:
            try:
                # Ensure directory exists
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)

                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self._cache_data, f, indent=2)

                if self.verbose.request_cache:
                    log.print_normal(f"Saved cache to {self.cache_file}")

            except OSError as e:
                log.print_warn(f"Error saving cache to {self.cache_file}: {e}")

    def _clean_expired_entries(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = []

        for key, entry in self._cache_data.items():
            if current_time - entry.get("timestamp", 0) > self.expiry_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache_data[key]

        if expired_keys and self.verbose.request_cache:
            log.print_normal(f"Cleaned {len(expired_keys)} expired cache entries")

    def _generate_key(
        self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a cache key from method, endpoint, and parameters.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters or request body

        Returns:
            A unique cache key
        """
        # Create a string representation of the request
        key_parts = [method.upper(), endpoint]

        if params:
            # Sort parameters for consistent key generation
            sorted_params = sorted(params.items())
            key_parts.append(json.dumps(sorted_params, sort_keys=True))

        key_string = "|".join(key_parts)

        # Use hash for shorter, consistent keys
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(
        self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            params: Query parameters or request body

        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            key = self._generate_key(method, endpoint, params)

            if key not in self._cache_data:
                return None

            entry = self._cache_data[key]
            current_time = time.time()

            # Check if entry is expired
            if current_time - entry.get("timestamp", 0) > self.expiry_seconds:
                del self._cache_data[key]
                self._save_cache()
                return None

            if self.verbose.request_cache:
                log.print_normal(f"Cache hit for {method} {endpoint}")

            return entry.get("data")

    def set(
        self, method: str, endpoint: str, data: Any, params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store a value in cache.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            data: Data to cache
            params: Query parameters or request body
        """
        with self._lock:
            key = self._generate_key(method, endpoint, params)

            self._cache_data[key] = {
                "data": data,
                "timestamp": time.time(),
                "method": method,
                "endpoint": endpoint,
                "params": params,
            }

            if self.verbose.request_cache:
                log.print_normal(f"Cached {method} {endpoint}")

            self._save_cache()

    # pylint: disable=too-many-branches
    def clear(self, method: str | None = None, endpoint: str | None = None) -> None:
        """Clear cache entries.

        Args:
            method: If provided, only clear entries with this HTTP method
            endpoint: If provided, only clear entries with this endpoint
        """
        with self._lock:
            if method is not None or endpoint is not None:
                # Remove entries that match the provided criteria
                keys_to_remove = []
                for key, entry in self._cache_data.items():
                    should_remove = True

                    # If both method and endpoint are provided, both must match
                    if method is not None and endpoint is not None:
                        if entry.get("method") != method or entry.get("endpoint") != endpoint:
                            should_remove = False
                    # If only method is provided, check method only
                    elif method is not None:
                        if entry.get("method") != method:
                            should_remove = False
                    # If only endpoint is provided, check endpoint only
                    elif endpoint is not None:
                        if entry.get("endpoint") != endpoint:
                            should_remove = False

                    if should_remove:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del self._cache_data[key]

                if self.verbose.request_cache:
                    log.print_normal(f"Cleared {len(keys_to_remove)} cache entries")
            else:
                # Clear all entries if no filters provided
                cleared_count = len(self._cache_data)
                self._cache_data = {}
                if self.verbose.request_cache:
                    log.print_normal(f"Cleared all {cleared_count} cache entries")

            self._save_cache()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            current_time = time.time()
            active_entries = 0
            expired_entries = 0

            for entry in self._cache_data.values():
                if current_time - entry.get("timestamp", 0) <= self.expiry_seconds:
                    active_entries += 1
                else:
                    expired_entries += 1

            return {
                "total_entries": len(self._cache_data),
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "expiry_seconds": self.expiry_seconds,
                "cache_file": str(self.cache_file),
            }
