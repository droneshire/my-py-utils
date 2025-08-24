import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
from ryutils import log

from ryutils.json_cache import JsonCache
from ryutils.verbose import Verbose


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

    def __post_init__(self) -> None:
        if self.verbose.requests:
            log.print_bright(f"Initialized RequestsHelper for {self.base_url}")
        if self.cache is None and self.cache_expiry_seconds is not None:
            assert (
                self.cache_file is not None
            ), "Cache file must be provided if cache_expiry_seconds is set"
            self.cache = JsonCache(
                cache_file=self.cache_file,
                expiry_seconds=self.cache_expiry_seconds,
                verbose=self.verbose,
            )
        else:
            log.print_warn("No cache file provided, so no cache will be used")

        # Add thread lock for protecting log file operations
        self._log_lock = threading.Lock()

    def log_request_info(self, json_data: Dict[str, Any]) -> None:
        """Log request information to file in a thread-safe manner."""
        if not self.log_requests:
            return

        with self._log_lock:
            if not self.log_file.exists() or self.fresh_log:
                # Create new log file with initial entry
                timestamp = datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")
                log_data = [{timestamp: json_data}]
                with open(self.log_file, "w", encoding="utf-8") as f:
                    json.dump(log_data, f, indent=2)
                self.fresh_log = False
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

        response = requests.get(url, headers=self.session.headers, params=params, timeout=10)
        try:
            response.raise_for_status()
            if self.verbose.requests_response:
                log.print_bright(f"Response: {response.json()}")
        except requests.HTTPError as e:
            # log the API's error payload
            try:
                err = response.json()
            except ValueError:
                err = response.text
            log.print_fail(f"Error getting from {url}: {err}")
            e.args = (*e.args, err)
            raise e
        finally:
            try:
                response_final = response.json()
            except ValueError:
                response_final = response.text
            self.log_request_info(
                {
                    "GET": {
                        "url": url,
                        "params": params,
                        "headers": self.session.headers,
                        "response": response_final,
                        "cookies": self.session.cookies,
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

        response = requests.put(
            url, headers=self.session.headers, json=json_dict, params=params, timeout=10
        )
        try:
            response.raise_for_status()
            try:
                response_final = response.json()
            except ValueError:
                response_final = response.text
            if self.verbose.requests_response:
                log.print_bright(f"Response: {response_final}")
            # Clear the cache as since we PUT, we likely invalidated it
            if self.cache is not None:
                self.cache.clear(endpoint=cache_clear_path or path)
        except requests.HTTPError as e:
            # log the API's error payload
            try:
                response_final = response.json()
            except ValueError:
                response_final = response.text
            log.print_fail(f"Error putting to {url}: {response_final}")
            e.args = (*e.args, response_final)
            raise e
        finally:

            self.log_request_info(
                {
                    "PUT": {
                        "url": url,
                        "json": json_dict,
                        "params": params,
                        "headers": self.session.headers,
                        "response": response_final,
                        "cookies": self.session.cookies,
                    }
                }
            )
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

        response = requests.post(
            url,
            headers=self.session.headers,
            json=json_dict,
            timeout=10,
            cookies=self.session.cookies,
        )

        try:
            response.raise_for_status()
            try:
                response_final = response.json()
            except ValueError:
                response_final = response.text
            if self.verbose.requests_response:
                log.print_bright(f"Response: {response.json()}")
            # Clear the cache as since we POST, we likely invalidated it
            if self.cache is not None:
                self.cache.clear(endpoint=cache_clear_path or path)
        except requests.HTTPError as e:
            # log the API's error payload
            try:
                response_final = response.json()
            except ValueError:
                response_final = response.text
            log.print_fail(f"Error posting to {url}")
            e.args = (*e.args, response_final[:1000])
            raise e
        finally:
            self.log_request_info(
                {
                    "POST": {
                        "url": url,
                        "json": json_dict,
                        "params": params,
                        "headers": self.session.headers,
                        "response": response_final,
                        "cookies": self.session.cookies,
                    }
                }
            )
        return response_final

    def delete(self, path: str, cache_clear_path: str | None = None) -> None:
        url = f"{self.base_url}{path}"

        if self.verbose.requests_url or self.verbose.requests:
            log.print_bright(f"DELETE {url}")

        if not self.receive_enabled:
            log.print_bright(f"Receive disabled: DELETE {url}")
            return

        response = requests.delete(url, headers=self.session.headers, timeout=10)

        try:
            response.raise_for_status()
            try:
                response_final = response.json()
            except ValueError:
                response_final = response.text
            if self.verbose.requests_response:
                log.print_bright(f"Response: {response.json()}")
            # Clear the cache as since we DELETE, we likely invalidated it
            if self.cache is not None:
                self.cache.clear(endpoint=cache_clear_path or path)
        except requests.HTTPError as e:
            # log the API's error payload
            try:
                response_final = response.json()
            except ValueError:
                response_final = response.text
            log.print_fail(f"Error deleting {url}: {response_final}")
            e.args = (*e.args, response_final)
            raise e
        finally:
            self.log_request_info(
                {
                    "DELETE": {
                        "url": url,
                        "headers": self.session.headers,
                        "response": response_final,
                        "cookies": self.session.cookies,
                    }
                }
            )
