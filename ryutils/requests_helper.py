import argparse
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ryutils import log
from ryutils.json_cache import JsonCache
from ryutils.verbose import Verbose


# Configure retry strategy for all requests
def create_retry_strategy(max_retries: int = 0) -> Retry:
    """Create a retry strategy with exponential backoff.

    Note: Set max_retries=0 to disable urllib3 retries when using manual retry logic.
    The manual retry logic in _make_request_with_retry handles all retries.
    """
    return Retry(
        total=max_retries,  # Total number of retries (0 = disabled, handled manually)
        backoff_factor=1,  # Base delay between retries
        status_forcelist=[408, 429, 500, 502, 503, 504],  # Retry on these status codes
        allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],  # Allow retries on all methods
        respect_retry_after_header=True,  # Respect Retry-After headers
    )


def add_request_helper_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments for request helper."""
    request_helper_parser = parser.add_argument_group("request-helper-options")
    request_helper_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode",
    )
    request_helper_parser.add_argument(
        "--receive-disabled",
        action="store_true",
        help="Disable receiving requests (GET/DELETE)",
    )
    request_helper_parser.add_argument(
        "--send-disabled",
        action="store_true",
        help="Disable sending requests (PUT/POST)",
    )
    request_helper_parser.add_argument(
        "--ignore-cache",
        action="store_true",
        help="Ignore cache",
    )
    request_helper_parser.add_argument(
        "--clear-logs",
        action="store_true",
        help="Clear logs",
    )


@dataclass
class RequestsHelper:
    verbose: Verbose
    base_url: str
    log_file: Path
    session: requests.Session = field(default_factory=requests.Session, init=False)
    log_requests: bool = False
    fresh_log: bool = False
    receive_enabled: bool = True
    send_enabled: bool = True
    cache: Optional[JsonCache] = None
    cache_file: Optional[Path] = None
    cache_expiry_seconds: Optional[int] = None
    timeout: int = 30  # Increased default timeout
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self) -> None:
        if self.verbose.requests:
            log.print_bright(f"Initialized RequestsHelper for {self.base_url}")

        # Configure retry strategy - disable urllib3 retries since we handle retries manually
        retry_strategy = create_retry_strategy(max_retries=0)
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        if (
            self.cache is None
            and self.cache_expiry_seconds is not None
            and self.cache_file is not None
        ):
            log.print_bright(f"{'*' * 100}")
            log.print_bright(f"Initializing cache for {self.cache_file}")
            log.print_bright(f"{'*' * 100}")
            self.cache = JsonCache(
                cache_file=self.cache_file,
                expiry_seconds=self.cache_expiry_seconds,
                verbose=self.verbose,
            )

    # pylint: disable=too-many-branches
    def _make_request_with_retry(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Make a request with retry logic and better error handling."""
        last_exception: Optional[requests.exceptions.RequestException] = None

        for attempt in range(self.max_retries + 1):
            try:
                if self.verbose.requests:
                    log.print_bright(
                        f"{method} {url} (attempt {attempt + 1}/{self.max_retries + 1})"
                    )

                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                response.raise_for_status()
                return response

            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)  # Exponential backoff
                    log.print_warn(
                        f"Request timed out, retrying in {delay:.1f}s... "
                        f"(attempt {attempt + 1}/{self.max_retries + 1}) {last_exception}"
                    )
                    time.sleep(delay)
                else:
                    log.print_fail(f"Request timed out after {self.max_retries + 1} attempts")

            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)
                    log.print_warn(
                        f"Connection error, retrying in {delay:.1f}s... "
                        f"(attempt {attempt + 1}/{self.max_retries + 1}) {last_exception}"
                    )
                    time.sleep(delay)
                else:
                    log.print_fail(f"Connection failed after {self.max_retries + 1} attempts")

            except requests.exceptions.RequestException as e:
                last_exception = e

                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)
                    log.print_warn(
                        f"Request failed, retrying in {delay:.1f}s... "
                        f"(attempt {attempt + 1}/{self.max_retries + 1}) {last_exception}"
                    )
                    time.sleep(delay)
                else:
                    # Extract response data if available (e.g., from HTTPError)
                    # Only build full error message after all retries exhausted
                    response_data = None
                    if hasattr(e, "response") and e.response is not None:
                        try:
                            response_data = e.response.json()
                        except (ValueError, AttributeError):
                            response_data = getattr(e.response, "text", None)

                    error_msg = str(last_exception)
                    if response_data is not None:
                        error_msg += f"\nResponse data: {response_data}"
                    log.print_fail(
                        f"Request failed after {self.max_retries + 1} attempts: {error_msg}"
                    )

        # If we get here, all retries failed
        if last_exception is not None:
            raise last_exception
        raise requests.exceptions.RequestException("All retries failed")

    def log_request_info(self, json_data: Dict[str, Any]) -> None:
        if not self.log_requests:
            return

        json_data["cookies"] = dict(self.session.cookies)

        # If fresh_log is True, delete existing file and create a new one (only on first call)
        # After creating the fresh file, reset fresh_log to False so subsequent
        # requests append to the same file
        if self.fresh_log:
            # Delete existing file if it exists to start fresh
            if self.log_file.exists():
                self.log_file.unlink()
            # Reset fresh_log after deleting so subsequent requests append
            self.fresh_log = False

        if not self.log_file.exists():
            # Create new log file with initial entry
            timestamp = datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")
            log_data = [{timestamp: json_data}]
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2)
        else:
            # Read existing log file
            with open(self.log_file, "r", encoding="utf-8") as f:
                try:
                    log_data = json.load(f)
                except json.JSONDecodeError:
                    log_data = []

            # Add new entry
            timestamp = datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")
            log_data.append({timestamp: json_data})

            # Write updated data back
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2)

    def _extract_response_data(self, response: Optional[requests.Response]) -> Any:
        """Extract JSON or text from response.

        Args:
            response: The requests Response object, or None

        Returns:
            Parsed JSON if available, otherwise response text, or empty string if None
        """
        if response is None:
            return ""
        try:
            return response.json()
        except (ValueError, AttributeError):
            return getattr(response, "text", "")

    def _extract_error_message(self, e: Exception, response: Optional[requests.Response]) -> Any:
        """Extract error message from exception and response.

        Args:
            e: The exception that occurred
            response: The requests Response object if available, or None

        Returns:
            Error message (string, dict, or list), preferring response data if available
        """
        if isinstance(e, requests.HTTPError) and response is not None:
            return self._extract_response_data(response)
        return str(e)

    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-statements
    def _make_request(
        self,
        method: str,
        path: str,
        json_dict: Optional[Union[Dict[str, Any], List[Any]]] = None,
        params: Optional[dict] = None,
        cache_clear_path: Optional[str] = None,
        should_cache: bool = False,
        enabled_check: bool = True,
        enabled_flag: bool = True,
    ) -> Any:
        """Generic request handler for all HTTP methods.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: URL path
            json_dict: JSON body for POST/PUT requests
            params: URL parameters
            cache_clear_path: Path to clear from cache (for PUT/POST/DELETE)
            should_cache: Whether to cache the response (for GET)
            enabled_check: Whether to check enabled flags
            enabled_flag: The enabled flag value (receive_enabled or send_enabled)

        Returns:
            Response data or error message
        """
        url = f"{self.base_url}{path}"

        # Verbose logging
        if self.verbose.requests_url:
            log.print_bright(f"{method} {url}")
        if self.verbose.requests:
            log_msg = f"{method} {url}"
            if json_dict is not None:
                log_msg += f" with json: {json_dict}"
            if params is not None:
                log_msg += f" and params: {params}"
            log.print_bright(log_msg)

        # Check if method is enabled
        if enabled_check and not enabled_flag:
            action = "Receive" if method in ("GET", "DELETE") else "Send"
            log.print_bright(f"{action} disabled: {method} {url}")
            return {} if method != "DELETE" else None

        # Cache check (for GET requests)
        if should_cache and self.cache is not None:
            cache_data = self.cache.get(method, path, params)
            if cache_data is not None:
                if self.verbose.requests:
                    log.print_bright(f"Cache hit for {method} {path}")
                return cache_data

        # Make the request
        response = None
        error_message = None
        try:
            kwargs: Dict[str, Any] = {}
            if params is not None:
                kwargs["params"] = params
            if json_dict is not None:
                kwargs["json"] = json_dict

            response = self._make_request_with_retry(method, url, **kwargs)

            if self.verbose.requests_response:
                log.print_bright(f"Response: {response.json()}")

        except requests.HTTPError as e:
            # log the API's error payload
            error_message = self._extract_error_message(e, response)
            # Format error message to match original style
            log.print_fail(f"Error {method.lower()}ing to {url}: {error_message}")
            e.args = (*e.args, error_message)
            raise e
        except Exception as e:
            error_message = str(e)
            # Format error message to match original style
            if method == "GET":
                log.print_fail(f"Unexpected error getting from {url}: {e}")
            elif method == "DELETE":
                log.print_fail(f"Unexpected error deleting {url}: {e}")
            else:
                log.print_fail(f"Unexpected error {method.lower()}ing to {url}: {e}")
            raise e
        finally:
            response_final = self._extract_response_data(response)
            if error_message is not None:
                response_final += f"\nError message: {error_message}"

            # Build log data
            log_data: Dict[str, Any] = {
                "url": url,
                "headers": dict(self.session.headers),
                "response": response_final,
            }
            if params is not None:
                log_data["params"] = params
            if json_dict is not None:
                log_data["json"] = json_dict

            self.log_request_info({method: log_data})

        # Cache management
        if should_cache and self.cache is not None and error_message is None:
            # Store in cache (for GET requests)
            self.cache.set(method, path, response_final, params)
        elif not should_cache and self.cache is not None:
            # Clear cache (for PUT/POST/DELETE)
            self.cache.clear(endpoint=cache_clear_path or path)

        return response_final

    def get(self, path: str, params: dict | None = None) -> Any:
        """GET request with optional caching."""
        return self._make_request(
            method="GET",
            path=path,
            params=params,
            should_cache=True,
            enabled_check=True,
            enabled_flag=self.receive_enabled,
        )

    def put(
        self,
        path: str,
        json_dict: Union[Dict[str, Any], List[Any], None] = None,
        params: dict | None = None,
        cache_clear_path: str | None = None,
    ) -> Any:
        """PUT request with cache clearing."""
        return self._make_request(
            method="PUT",
            path=path,
            json_dict=json_dict,
            params=params,
            cache_clear_path=cache_clear_path,
            enabled_check=True,
            enabled_flag=self.send_enabled,
        )

    def post(
        self,
        path: str,
        json_dict: Union[Dict[str, Any], List[Any], None] = None,
        params: dict | None = None,
        cache_clear_path: str | None = None,
    ) -> Any:
        """POST request with cache clearing."""
        return self._make_request(
            method="POST",
            path=path,
            json_dict=json_dict,
            params=params,
            cache_clear_path=cache_clear_path,
            enabled_check=True,
            enabled_flag=self.send_enabled,
        )

    def patch(
        self,
        path: str,
        json_dict: Union[Dict[str, Any], List[Any], None] = None,
        params: dict | None = None,
        cache_clear_path: str | None = None,
    ) -> Any:
        """PATCH request with cache clearing."""
        return self._make_request(
            method="PATCH",
            path=path,
            json_dict=json_dict,
            params=params,
            cache_clear_path=cache_clear_path,
            enabled_check=True,
            enabled_flag=self.send_enabled,
        )

    def delete(self, path: str, cache_clear_path: str | None = None) -> None:
        """DELETE request with cache clearing."""
        self._make_request(
            method="DELETE",
            path=path,
            cache_clear_path=cache_clear_path,
            enabled_check=True,
            enabled_flag=self.receive_enabled,
        )
