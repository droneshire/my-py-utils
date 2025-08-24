# pylint: disable=protected-access
"""
Tests for request caching functionality.
"""

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ryutils.json_cache import JsonCache
from ryutils.requests_helper import RequestsHelper
from ryutils.verbose import Verbose


class JsonCacheTest(unittest.TestCase):
    """Test the JsonCache class functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = Path(self.temp_dir) / "test_cache.json"
        self.verbose = Verbose()
        self.cache = JsonCache(
            cache_file=self.cache_file,
            expiry_seconds=1,  # 1 second for quick testing
            verbose=self.verbose,
        )

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        if self.cache_file.exists():
            self.cache_file.unlink()
        Path(self.temp_dir).rmdir()

    def test_cache_initialization(self) -> None:
        """Test cache initialization."""
        self.assertEqual(self.cache.expiry_seconds, 1)
        self.assertEqual(self.cache.cache_file, self.cache_file)
        self.assertEqual(len(self.cache._cache_data), 0)

    def test_cache_set_and_get(self) -> None:
        """Test basic cache set and get operations."""
        test_data = {"test": "data"}

        # Test cache miss
        result = self.cache.get("GET", "/test", {"param": "value"})
        self.assertIsNone(result)

        # Test cache set
        self.cache.set("GET", "/test", test_data, {"param": "value"})

        # Test cache hit
        result = self.cache.get("GET", "/test", {"param": "value"})
        self.assertEqual(result, test_data)

    def test_cache_key_generation(self) -> None:
        """Test that cache keys are generated consistently."""
        # Same parameters should generate same key
        key1 = self.cache._generate_key("GET", "/test", {"a": 1, "b": 2})
        key2 = self.cache._generate_key("GET", "/test", {"b": 2, "a": 1})
        self.assertEqual(key1, key2)

        # Different parameters should generate different keys
        key3 = self.cache._generate_key("GET", "/test", {"a": 1, "b": 3})
        self.assertNotEqual(key1, key3)

        # Different methods should generate different keys
        key4 = self.cache._generate_key("POST", "/test", {"a": 1, "b": 2})
        self.assertNotEqual(key1, key4)

    def test_cache_expiration(self) -> None:
        """Test that cache entries expire correctly."""
        test_data = {"test": "data"}

        # Set cache entry
        self.cache.set("GET", "/test", test_data)

        # Should be available immediately
        result = self.cache.get("GET", "/test")
        self.assertEqual(result, test_data)

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired now
        result = self.cache.get("GET", "/test")
        self.assertIsNone(result)

    def test_cache_persistence(self) -> None:
        """Test that cache persists to disk and loads correctly."""
        test_data = {"test": "data"}

        # Set cache entry
        self.cache.set("GET", "/test", test_data, {"param": "value"})

        # Create new cache instance (should load from file)
        new_cache = JsonCache(cache_file=self.cache_file, expiry_seconds=1, verbose=self.verbose)

        # Should find the cached data
        result = new_cache.get("GET", "/test", {"param": "value"})
        self.assertEqual(result, test_data)

    def test_cache_cleanup(self) -> None:
        """Test that expired entries are cleaned up on load."""
        # Create cache with longer expiry for this test
        cache = JsonCache(cache_file=self.cache_file, expiry_seconds=10, verbose=self.verbose)

        # Add some test data
        cache.set("GET", "/test1", {"data": "1"})
        cache.set("GET", "/test2", {"data": "2"})

        # Manually expire one entry
        cache._cache_data["test_key"] = {
            "data": {"data": "expired"},
            "timestamp": time.time() - 20,  # 20 seconds ago
            "method": "GET",
            "endpoint": "/expired",
            "params": None,
        }

        # Save to disk
        cache._save_cache()

        # Create new cache instance (should clean expired entries)
        new_cache = JsonCache(cache_file=self.cache_file, expiry_seconds=10, verbose=self.verbose)

        # Should only have the non-expired entries
        self.assertLess(len(new_cache._cache_data), len(cache._cache_data))

    def test_cache_clear(self) -> None:
        """Test cache clear functionality."""
        # Add multiple test entries
        self.cache.set("GET", "/test1", {"data": "1"})
        self.cache.set("POST", "/test1", {"data": "2"})
        self.cache.set("GET", "/test2", {"data": "3"})
        self.cache.set("POST", "/test2", {"data": "4"})

        # Verify all data is cached
        self.assertEqual(self.cache.get("GET", "/test1"), {"data": "1"})
        self.assertEqual(self.cache.get("POST", "/test1"), {"data": "2"})
        self.assertEqual(self.cache.get("GET", "/test2"), {"data": "3"})
        self.assertEqual(self.cache.get("POST", "/test2"), {"data": "4"})

        # Test clearing all cache
        self.cache.clear()
        self.assertIsNone(self.cache.get("GET", "/test1"))
        self.assertIsNone(self.cache.get("POST", "/test1"))
        self.assertIsNone(self.cache.get("GET", "/test2"))
        self.assertIsNone(self.cache.get("POST", "/test2"))

    def test_cache_clear_by_method(self) -> None:
        """Test clearing cache entries by HTTP method."""
        # Add multiple test entries
        self.cache.set("GET", "/test1", {"data": "1"})
        self.cache.set("POST", "/test1", {"data": "2"})
        self.cache.set("GET", "/test2", {"data": "3"})
        self.cache.set("POST", "/test2", {"data": "4"})

        # Clear only GET requests
        self.cache.clear(method="GET")

        # GET requests should be gone
        self.assertIsNone(self.cache.get("GET", "/test1"))
        self.assertIsNone(self.cache.get("GET", "/test2"))

        # POST requests should remain
        self.assertEqual(self.cache.get("POST", "/test1"), {"data": "2"})
        self.assertEqual(self.cache.get("POST", "/test2"), {"data": "4"})

    def test_cache_clear_by_endpoint(self) -> None:
        """Test clearing cache entries by endpoint."""
        # Add multiple test entries
        self.cache.set("GET", "/test1", {"data": "1"})
        self.cache.set("POST", "/test1", {"data": "2"})
        self.cache.set("GET", "/test2", {"data": "3"})
        self.cache.set("POST", "/test2", {"data": "4"})

        # Clear only /test1 endpoint
        self.cache.clear(endpoint="/test1")

        # /test1 entries should be gone
        self.assertIsNone(self.cache.get("GET", "/test1"))
        self.assertIsNone(self.cache.get("POST", "/test1"))

        # /test2 entries should remain
        self.assertEqual(self.cache.get("GET", "/test2"), {"data": "3"})
        self.assertEqual(self.cache.get("POST", "/test2"), {"data": "4"})

    def test_cache_clear_by_method_and_endpoint(self) -> None:
        """Test clearing cache entries by both method and endpoint."""
        # Add multiple test entries
        self.cache.set("GET", "/test1", {"data": "1"})
        self.cache.set("POST", "/test1", {"data": "2"})
        self.cache.set("GET", "/test2", {"data": "3"})
        self.cache.set("POST", "/test2", {"data": "4"})

        # Clear only GET requests for /test1
        self.cache.clear(method="GET", endpoint="/test1")

        # Only GET /test1 should be gone
        self.assertIsNone(self.cache.get("GET", "/test1"))

        # All others should remain
        self.assertEqual(self.cache.get("POST", "/test1"), {"data": "2"})
        self.assertEqual(self.cache.get("GET", "/test2"), {"data": "3"})
        self.assertEqual(self.cache.get("POST", "/test2"), {"data": "4"})

    def test_cache_clear_by_method_and_endpoint_comprehensive(self) -> None:
        """Test comprehensive clearing scenarios with method and endpoint combinations."""
        # Add more diverse test entries
        self.cache.set("GET", "/api/events", {"data": "events"})
        self.cache.set("POST", "/api/events", {"data": "create_event"})
        self.cache.set("GET", "/api/users", {"data": "users"})
        self.cache.set("POST", "/api/users", {"data": "create_user"})
        self.cache.set("PUT", "/api/events", {"data": "update_event"})
        self.cache.set("DELETE", "/api/events", {"data": "delete_event"})

        # Test 1: Clear only GET /api/events
        self.cache.clear(method="GET", endpoint="/api/events")

        # GET /api/events should be gone
        self.assertIsNone(self.cache.get("GET", "/api/events"))

        # All others should remain
        self.assertEqual(self.cache.get("POST", "/api/events"), {"data": "create_event"})
        self.assertEqual(self.cache.get("GET", "/api/users"), {"data": "users"})
        self.assertEqual(self.cache.get("POST", "/api/users"), {"data": "create_user"})
        self.assertEqual(self.cache.get("PUT", "/api/events"), {"data": "update_event"})
        self.assertEqual(self.cache.get("DELETE", "/api/events"), {"data": "delete_event"})

        # Test 2: Clear only POST /api/users
        self.cache.clear(method="POST", endpoint="/api/users")

        # POST /api/users should be gone
        self.assertIsNone(self.cache.get("POST", "/api/users"))

        # All others should remain
        self.assertEqual(self.cache.get("POST", "/api/events"), {"data": "create_event"})
        self.assertEqual(self.cache.get("GET", "/api/users"), {"data": "users"})
        self.assertEqual(self.cache.get("PUT", "/api/events"), {"data": "update_event"})
        self.assertEqual(self.cache.get("DELETE", "/api/events"), {"data": "delete_event"})

    def test_cache_clear_edge_cases(self) -> None:
        """Test edge cases for cache clearing."""
        # Add test entries
        self.cache.set("GET", "/test", {"data": "1"})
        self.cache.set("POST", "/test", {"data": "2"})
        self.cache.set("GET", "/other", {"data": "3"})

        # Test clearing with non-existent method
        self.cache.clear(method="PUT", endpoint="/test")

        # Nothing should be deleted since PUT /test doesn't exist
        self.assertEqual(self.cache.get("GET", "/test"), {"data": "1"})
        self.assertEqual(self.cache.get("POST", "/test"), {"data": "2"})
        self.assertEqual(self.cache.get("GET", "/other"), {"data": "3"})

        # Test clearing with non-existent endpoint
        self.cache.clear(method="GET", endpoint="/nonexistent")

        # Nothing should be deleted since GET /nonexistent doesn't exist
        self.assertEqual(self.cache.get("GET", "/test"), {"data": "1"})
        self.assertEqual(self.cache.get("POST", "/test"), {"data": "2"})
        self.assertEqual(self.cache.get("GET", "/other"), {"data": "3"})

        # Test clearing with both non-existent
        self.cache.clear(method="PUT", endpoint="/nonexistent")

        # Nothing should be deleted
        self.assertEqual(self.cache.get("GET", "/test"), {"data": "1"})
        self.assertEqual(self.cache.get("POST", "/test"), {"data": "2"})
        self.assertEqual(self.cache.get("GET", "/other"), {"data": "3"})

    def test_cache_stats(self) -> None:
        """Test cache statistics."""
        # Add some test data
        self.cache.set("GET", "/test1", {"data": "1"})
        self.cache.set("GET", "/test2", {"data": "2"})

        stats = self.cache.get_stats()

        self.assertEqual(stats["total_entries"], 2)
        self.assertEqual(stats["active_entries"], 2)
        self.assertEqual(stats["expired_entries"], 0)
        self.assertEqual(stats["expiry_seconds"], 1)
        self.assertEqual(stats["cache_file"], str(self.cache_file))


class RequestsHelperCacheTest(unittest.TestCase):
    """Test RequestsHelper with caching enabled."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = Path(self.temp_dir) / "test_requests_cache.json"
        self.log_file = Path(self.temp_dir) / "test_requests_log.json"
        self.verbose = Verbose()

        # Create RequestsHelper with caching enabled
        self.requests_helper = RequestsHelper(
            log_file=self.log_file,
            verbose=self.verbose,
            base_url="https://api.example.com",
            cache_expiry_seconds=1,  # 1 second for quick testing
            cache_file=self.cache_file,
        )

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        if self.cache_file.exists():
            self.cache_file.unlink()
        if self.log_file.exists():
            self.log_file.unlink()
        Path(self.temp_dir).rmdir()

    @patch.object(RequestsHelper, '_make_request_with_retry')
    def test_get_with_cache(self, mock_request: Mock) -> None:
        """Test that GET requests are cached."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # First request - should hit the API
        result1 = self.requests_helper.get("/test", {"param": "value"})
        self.assertEqual(result1, {"test": "data"})
        self.assertEqual(mock_request.call_count, 1)

        # Second request - should hit cache
        result2 = self.requests_helper.get("/test", {"param": "value"})
        self.assertEqual(result2, {"test": "data"})
        self.assertEqual(mock_request.call_count, 1)  # Should not have called API again

        # Different parameters - should hit API again
        result3 = self.requests_helper.get("/test", {"param": "different"})
        self.assertEqual(result3, {"test": "data"})
        self.assertEqual(mock_request.call_count, 2)

    @patch.object(RequestsHelper, '_make_request_with_retry')
    def test_get_without_cache(self, mock_request: Mock) -> None:
        """Test that RequestsHelper works without cache."""
        # Create RequestsHelper without cache
        requests_helper = RequestsHelper(
            log_file=self.log_file,
            verbose=self.verbose,
            base_url="https://api.example.com",
        )

        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Both requests should hit the API
        result1 = requests_helper.get("/test")
        result2 = requests_helper.get("/test")

        self.assertEqual(result1, {"test": "data"})
        self.assertEqual(result2, {"test": "data"})
        self.assertEqual(mock_request.call_count, 2)

    @patch.object(RequestsHelper, '_make_request_with_retry')
    def test_cache_expiration_in_requests(self, mock_request: Mock) -> None:
        """Test that cache expiration works in RequestsHelper."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # First request
        result1 = self.requests_helper.get("/test")
        self.assertEqual(result1, {"test": "data"})
        self.assertEqual(mock_request.call_count, 1)

        # Wait for cache to expire
        time.sleep(1.1)

        # Second request after expiration
        result2 = self.requests_helper.get("/test")
        self.assertEqual(result2, {"test": "data"})
        self.assertEqual(mock_request.call_count, 2)  # Should call API again

    @patch.object(RequestsHelper, '_make_request_with_retry')
    def test_post_not_cached(self, mock_request: Mock) -> None:
        """Test that POST requests are not cached."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Both POST requests should hit the API
        result1 = self.requests_helper.post("/test", {"data": "test"})
        result2 = self.requests_helper.post("/test", {"data": "test"})

        self.assertEqual(result1, {"test": "data"})
        self.assertEqual(result2, {"test": "data"})
        self.assertEqual(mock_request.call_count, 2)

    def test_cache_initialization_with_expiry(self) -> None:
        """Test that cache is initialized when expiry is provided."""
        requests_helper = RequestsHelper(
            log_file=self.log_file,
            verbose=self.verbose,
            base_url="https://api.example.com",
            cache_expiry_seconds=3600,
            cache_file=self.cache_file,
        )

        self.assertIsNotNone(requests_helper.cache)
        if requests_helper.cache is not None:  # Add null check
            self.assertEqual(requests_helper.cache.expiry_seconds, 3600)

    def test_cache_initialization_without_expiry(self) -> None:
        """Test that cache is not initialized when no expiry is provided."""
        requests_helper = RequestsHelper(
            log_file=self.log_file,
            verbose=self.verbose,
            base_url="https://api.example.com",
            cache_file=self.cache_file,
        )

        self.assertIsNone(requests_helper.cache)

    @patch.object(RequestsHelper, '_make_request_with_retry')
    def test_post_with_cache_clear_path(self, mock_request: Mock) -> None:
        """Test that POST requests clear cache with custom path."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Add some cached data first
        assert self.requests_helper.cache is not None
        self.requests_helper.cache.set("GET", "/api/events", {"cached": "data"})
        self.requests_helper.cache.set("GET", "/api/events/123", {"cached": "specific"})
        self.requests_helper.cache.set("GET", "/api/users", {"cached": "users"})

        # Verify cache has data
        self.assertEqual(self.requests_helper.cache.get("GET", "/api/events"), {"cached": "data"})
        self.assertEqual(
            self.requests_helper.cache.get("GET", "/api/events/123"), {"cached": "specific"}
        )
        self.assertEqual(self.requests_helper.cache.get("GET", "/api/users"), {"cached": "users"})

        # POST to /api/events/123 but clear cache for /api/events
        result = self.requests_helper.post(
            "/api/events/123", {"data": "test"}, cache_clear_path="/api/events"
        )

        self.assertEqual(result, {"test": "data"})
        self.assertEqual(mock_request.call_count, 1)

        # Cache for /api/events should be cleared
        self.assertIsNone(self.requests_helper.cache.get("GET", "/api/events"))

        # Cache for /api/events/123 should remain (since we cleared
        # /api/events, not /api/events/123)
        self.assertEqual(
            self.requests_helper.cache.get("GET", "/api/events/123"), {"cached": "specific"}
        )

        # Cache for /api/users should remain
        self.assertEqual(self.requests_helper.cache.get("GET", "/api/users"), {"cached": "users"})

    @patch.object(RequestsHelper, '_make_request_with_retry')
    def test_put_with_cache_clear_path(self, mock_request: Mock) -> None:
        """Test that PUT requests clear cache with custom path."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Add some cached data first
        assert self.requests_helper.cache is not None
        self.requests_helper.cache.set("GET", "/api/events", {"cached": "data"})
        self.requests_helper.cache.set("GET", "/api/events/123", {"cached": "specific"})
        self.requests_helper.cache.set("GET", "/api/users", {"cached": "users"})

        # Verify cache has data
        self.assertEqual(self.requests_helper.cache.get("GET", "/api/events"), {"cached": "data"})
        self.assertEqual(
            self.requests_helper.cache.get("GET", "/api/events/123"), {"cached": "specific"}
        )
        self.assertEqual(self.requests_helper.cache.get("GET", "/api/users"), {"cached": "users"})

        # PUT to /api/events/123 but clear cache for /api/events
        result = self.requests_helper.put(
            "/api/events/123", {"data": "test"}, cache_clear_path="/api/events"
        )

        self.assertEqual(result, {"test": "data"})
        self.assertEqual(mock_request.call_count, 1)

        # Cache for /api/events should be cleared
        self.assertIsNone(self.requests_helper.cache.get("GET", "/api/events"))

        # Cache for /api/events/123 should remain
        self.assertEqual(
            self.requests_helper.cache.get("GET", "/api/events/123"), {"cached": "specific"}
        )

        # Cache for /api/users should remain
        self.assertEqual(self.requests_helper.cache.get("GET", "/api/users"), {"cached": "users"})

    @patch.object(RequestsHelper, '_make_request_with_retry')
    def test_delete_with_cache_clear_path(self, mock_request: Mock) -> None:
        """Test that DELETE requests clear cache with custom path."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Add some cached data first
        assert self.requests_helper.cache is not None
        self.requests_helper.cache.set("GET", "/api/events", {"data": "cached"})
        self.requests_helper.cache.set("GET", "/api/events/123", {"data": "specific"})
        self.requests_helper.cache.set("GET", "/api/users", {"data": "users"})

        # Verify cache has data
        self.assertEqual(self.requests_helper.cache.get("GET", "/api/events"), {"data": "cached"})
        self.assertEqual(
            self.requests_helper.cache.get("GET", "/api/events/123"), {"data": "specific"}
        )
        self.assertEqual(self.requests_helper.cache.get("GET", "/api/users"), {"data": "users"})

        # DELETE /api/events/123 but clear cache for /api/events
        self.requests_helper.delete("/api/events/123", cache_clear_path="/api/events")

        self.assertEqual(mock_request.call_count, 1)

        # Cache for /api/events should be cleared
        self.assertIsNone(self.requests_helper.cache.get("GET", "/api/events"))

        # Cache for /api/events/123 should remain
        self.assertEqual(
            self.requests_helper.cache.get("GET", "/api/events/123"), {"data": "specific"}
        )

        # Cache for /api/users should remain
        self.assertEqual(self.requests_helper.cache.get("GET", "/api/users"), {"data": "users"})

    @patch.object(RequestsHelper, '_make_request_with_retry')
    def test_post_without_cache_clear_path(self, mock_request: Mock) -> None:
        """Test that POST requests clear cache with default path when cache_clear_path is None."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Add some cached data first
        assert self.requests_helper.cache is not None
        self.requests_helper.cache.set("GET", "/api/events/123", {"cached": "specific"})
        self.requests_helper.cache.set("GET", "/api/users", {"cached": "users"})

        # Verify cache has data
        self.assertEqual(
            self.requests_helper.cache.get("GET", "/api/events/123"), {"cached": "specific"}
        )
        self.assertEqual(self.requests_helper.cache.get("GET", "/api/users"), {"cached": "users"})

        # POST to /api/events/123 without cache_clear_path (should use default path)
        result = self.requests_helper.post("/api/events/123", {"data": "test"})

        self.assertEqual(result, {"test": "data"})
        self.assertEqual(mock_request.call_count, 1)

        # Cache for /api/events/123 should be cleared (default behavior)
        self.assertIsNone(self.requests_helper.cache.get("GET", "/api/events/123"))

        # Cache for /api/users should remain
        self.assertEqual(self.requests_helper.cache.get("GET", "/api/users"), {"cached": "users"})

    @patch.object(RequestsHelper, '_make_request_with_retry')
    def test_post_cache_clear_path_with_different_methods(self, mock_request: Mock) -> None:
        """Test that cache clearing with custom path works for different HTTP methods."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response

        # Add cached data for different methods on the same endpoint
        assert self.requests_helper.cache is not None
        self.requests_helper.cache.set("GET", "/api/events", {"cached": "get_data"})
        self.requests_helper.cache.set("POST", "/api/events", {"cached": "post_data"})
        self.requests_helper.cache.set("PUT", "/api/events", {"cached": "put_data"})

        # Verify cache has data
        self.assertEqual(
            self.requests_helper.cache.get("GET", "/api/events"), {"cached": "get_data"}
        )
        self.assertEqual(
            self.requests_helper.cache.get("POST", "/api/events"), {"cached": "post_data"}
        )
        self.assertEqual(
            self.requests_helper.cache.get("PUT", "/api/events"), {"cached": "put_data"}
        )

        # POST to /api/events/123 but clear cache for /api/events
        result = self.requests_helper.post(
            "/api/events/123", {"data": "test"}, cache_clear_path="/api/events"
        )

        self.assertEqual(result, {"test": "data"})
        self.assertEqual(mock_request.call_count, 1)

        # All cache entries for /api/events should be cleared (all methods)
        self.assertIsNone(self.requests_helper.cache.get("GET", "/api/events"))
        self.assertIsNone(self.requests_helper.cache.get("POST", "/api/events"))
        self.assertIsNone(self.requests_helper.cache.get("PUT", "/api/events"))


if __name__ == "__main__":
    unittest.main()
