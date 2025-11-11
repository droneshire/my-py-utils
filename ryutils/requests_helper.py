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
def create_retry_strategy() -> Retry:
    """Create a retry strategy with exponential backoff."""
    return Retry(
        total=3,  # Total number of retries
        backoff_factor=1,  # Base delay between retries (1, 2, 4 seconds)
        status_forcelist=[408, 429, 500, 502, 503, 504],  # Retry on these status codes
        allowed_methods=["GET", "POST", "PUT", "DELETE"],  # Allow retries on all methods
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

        # Configure retry strategy
        retry_strategy = create_retry_strategy()
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
                    log.print_fail(
                        f"Request failed after {self.max_retries + 1} attempts: {last_exception}"
                    )

        # If we get here, all retries failed
        if last_exception is not None:
            raise last_exception
        raise requests.exceptions.RequestException("All retries failed")

    def log_request_info(self, json_data: Dict[str, Any]) -> None:
        if not self.log_requests:
            return

        json_data["cookies"] = dict(self.session.cookies)

        if not self.log_file.exists() or self.fresh_log:
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

    # pylint: disable=too-many-branches
    def get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        if self.verbose.requests_url:
            log.print_bright(f"GET {url}")

        if self.verbose.requests:
            log.print_bright(f"GET {url} with params: {params}")

        if not self.receive_enabled:
            log.print_bright(f"Receive disabled: GET {url}")
            return {}

        # Caching logic
        if self.cache is not None:
            cache_data = self.cache.get("GET", path, params)
            if cache_data is not None:
                if self.verbose.requests:
                    log.print_bright(f"Cache hit for GET {path}")
                return cache_data

        response = None
        try:
            response = self._make_request_with_retry("GET", url, params=params)

            if self.verbose.requests_response:
                log.print_bright(f"Response: {response.json()}")

        except requests.HTTPError as e:
            # log the API's error payload
            try:
                err = response.json() if response is not None else str(e)
            except (ValueError, AttributeError):
                err = getattr(response, "text", str(e)) if response is not None else str(e)
            log.print_fail(f"Error getting from {url}: {err}")
            e.args = (*e.args, err)
            raise e
        except Exception as e:
            log.print_fail(f"Unexpected error getting from {url}: {e}")
            raise e
        finally:
            try:
                response_final = response.json() if response is not None else ""
            except (ValueError, AttributeError):
                response_final = getattr(response, "text", "") if response is not None else ""
            self.log_request_info(
                {
                    "GET": {
                        "url": url,
                        "params": params,
                        "headers": dict(self.session.headers),
                        "response": response_final,
                    }
                }
            )

        # Store in cache
        if self.cache is not None:
            self.cache.set("GET", path, response_final, params)
        return response_final

    def put(
        self,
        path: str,
        json_dict: Union[Dict[str, Any], List[Any], None] = None,
        params: dict | None = None,
        cache_clear_path: str | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if self.verbose.requests_url:
            log.print_bright(f"PUT {url}")

        if self.verbose.requests:
            log.print_bright(f"PUT {url} with json: {json_dict} and params: {params}")

        if not self.send_enabled:
            log.print_bright(f"Send disabled: PUT {url}")
            return {}

        response = None
        try:
            response = self._make_request_with_retry("PUT", url, json=json_dict, params=params)

            if self.verbose.requests_response:
                log.print_bright(f"Response: {response.json()}")

        except requests.HTTPError as e:
            # log the API's error payload
            try:
                response_final = response.json() if response is not None else str(e)
            except (ValueError, AttributeError):
                response_final = (
                    getattr(response, "text", str(e)) if response is not None else str(e)
                )
            log.print_fail(f"Error putting to {url}: {response_final}")
            e.args = (*e.args, response_final)
            raise e
        except Exception as e:
            log.print_fail(f"Unexpected error putting to {url}: {e}")
            raise e
        finally:
            try:
                response_final = response.json() if response is not None else ""
            except (ValueError, AttributeError):
                response_final = getattr(response, "text", "") if response is not None else ""
            self.log_request_info(
                {
                    "PUT": {
                        "url": url,
                        "json": json_dict,
                        "params": params,
                        "headers": dict(self.session.headers),
                        "response": response_final,
                    }
                }
            )

        # Clear the cache as since we PUT, we likely invalidated it
        if self.cache is not None:
            self.cache.clear(endpoint=cache_clear_path or path)

        return response_final

    def post(
        self,
        path: str,
        json_dict: Union[Dict[str, Any], List[Any], None] = None,
        params: dict | None = None,
        cache_clear_path: str | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if self.verbose.requests_url:
            log.print_bright(f"POST {url}")

        if self.verbose.requests:
            log.print_bright(f"POST {url} with json: {json_dict} and params: {params}")

        if not self.send_enabled:
            log.print_bright(f"Send disabled: POST {url}")
            return {}

        response = None
        try:
            response = self._make_request_with_retry("POST", url, json=json_dict, params=params)

            if self.verbose.requests_response:
                log.print_bright(f"Response: {response.json()}")

        except requests.HTTPError as e:
            # log the API's error payload
            try:
                response_final = response.json() if response is not None else str(e)
            except (ValueError, AttributeError):
                response_final = (
                    getattr(response, "text", str(e)) if response is not None else str(e)
                )
            log.print_fail(f"Error posting to {url}: {response_final}")
            e.args = (*e.args, response_final)
            raise e
        except Exception as e:
            log.print_fail(f"Unexpected error posting to {url}: {e}")
            raise e
        finally:
            try:
                response_final = response.json() if response is not None else ""
            except (ValueError, AttributeError):
                response_final = getattr(response, "text", "") if response is not None else ""
            self.log_request_info(
                {
                    "POST": {
                        "url": url,
                        "json": json_dict,
                        "params": params,
                        "headers": dict(self.session.headers),
                        "response": response_final,
                    }
                }
            )

        # Clear the cache as since we POST, we likely invalidated it
        if self.cache is not None:
            self.cache.clear(endpoint=cache_clear_path or path)
        return response_final

    def delete(self, path: str, cache_clear_path: str | None = None) -> None:
        url = f"{self.base_url}{path}"

        if self.verbose.requests_url or self.verbose.requests:
            log.print_bright(f"DELETE {url}")

        if not self.receive_enabled:
            log.print_bright(f"Receive disabled: DELETE {url}")
            return

        response = None
        try:
            response = self._make_request_with_retry("DELETE", url)

            if self.verbose.requests_response:
                log.print_bright(f"Response: {response.json()}")

        except requests.HTTPError as e:
            # log the API's error payload
            try:
                response_final = response.json() if response is not None else str(e)
            except (ValueError, AttributeError):
                response_final = (
                    getattr(response, "text", str(e)) if response is not None else str(e)
                )
            log.print_fail(f"Error deleting {url}: {response_final}")
            e.args = (*e.args, response_final)
            raise e
        except Exception as e:
            log.print_fail(f"Unexpected error deleting {url}: {e}")
            raise e
        finally:
            try:
                response_final = response.json() if response is not None else ""
            except (ValueError, AttributeError):
                response_final = getattr(response, "text", "") if response is not None else ""
            self.log_request_info(
                {
                    "DELETE": {
                        "url": url,
                        "headers": dict(self.session.headers),
                        "response": response_final,
                    }
                }
            )

        # Clear the cache as since we DELETE, we likely invalidated it
        if self.cache is not None:
            self.cache.clear(endpoint=cache_clear_path or path)
