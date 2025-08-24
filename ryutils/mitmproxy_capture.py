"""
Mitmproxy integration for capturing headers and cookies from Upwork requests.

This module provides functionality to:
1. Start mitmproxy in the background
2. Capture specific requests (like fetch_work_history)
3. Extract headers and cookies from captured requests
4. Use captured data in subsequent requests

Chrome/Chromium:


Open Chrome Settings:
    Click the three dots menu → Settings
    Or go to chrome://settings/

    OR

    Click the three dots menu → More tools → Extensions
    Find "mitmproxy" in the list
    Click "Details"
    Click "Open proxy settings"

Navigate to Proxy Settings:
    Scroll down and click "Advanced"
    Under "System", click "Open your computer's proxy settings"
    Or go directly to chrome://settings/system

Configure Proxy:
    In the system proxy settings, enable "Manual proxy configuration"
    Set HTTP Proxy: 127.0.0.1
    Set Port: 8080 (or whatever port your mitmproxy is using)
    Check "Use this proxy server for all protocols"
    Click "Save"

"""

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ryutils import log
from ryutils.verbose import Verbose


class MitmproxyCapture:
    """
    Manages mitmproxy for capturing Upwork request headers and cookies.
    Workflow:
    1. Start mitmproxy to capture traffic to a .mitm file
    2. Convert .mitm to .har using mitmdump + savehar
    3. Extract relevant requests from .har
    """

    def __init__(self, port: int, verbose: Verbose, capture_dir: Optional[Path] = None) -> None:
        self.verbose = verbose
        self.capture_dir = capture_dir
        if self.capture_dir:
            self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.port = port

        timestamp = int(time.time())

        if self.capture_dir:
            self.capture_file = self.capture_dir / f"capture_{timestamp}.mitm"
        else:
            self.capture_file = Path(f"capture_{timestamp}.mitm")

        self.process: Optional[subprocess.Popen] = None

    def kill_mitmproxy(self) -> None:
        """Kill mitmproxy if running."""
        # Force kill if terminate times out
        subprocess.run(["pkill", "mitmproxy"], check=False)
        subprocess.run(["pkill", "mitmdump"], check=False)
        log.print_warn("Mitmproxy forcefully killed with pkill")

    def clear_cache(self) -> None:
        """Clear the cache."""
        if not self.capture_dir:
            return
        for file in self.capture_dir.glob("*.json"):
            file.unlink()
        log.print_ok("Cleared cache")

    def start_proxy(self) -> None:
        """Start mitmproxy in the background, saving to a .mitm file."""

        self.kill_mitmproxy()

        cmd = [
            "mitmdump",
            "--listen-port",
            str(self.port),
            "--set",
            "block_global=false",
            "-w",
            str(self.capture_file),
        ]
        if self.verbose.general:
            log.print_normal(f"Starting mitmproxy: {' '.join(cmd)}")
        self.process = subprocess.Popen(  # pylint: disable=consider-using-with
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        time.sleep(2)
        if self.process.poll() is None:
            log.print_ok(f"Mitmproxy started on port {self.port}")
            log.print_ok(f"Capture file: {self.capture_file}")
        else:
            _, stderr = self.process.communicate()
            log.print_fail(f"Failed to start mitmproxy: {stderr}")
            raise RuntimeError("Mitmproxy failed to start")

    def stop_proxy(self) -> None:
        """Stop mitmproxy if running."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
                log.print_ok("Mitmproxy stopped")
            except subprocess.TimeoutExpired:
                self.process.kill()
                log.print_warn("Mitmproxy forcefully killed")
            finally:
                self.process = None

    def convert_to_har(self, mitm_file: Path) -> Path:
        """Convert a .mitm file to .har using mitmdump and savehar."""
        # Find savehar.py location
        savehar_path = (
            subprocess.check_output(
                ["python", "-c", "import mitmproxy.addons.savehar as m; print(m.__file__)"]
            )
            .decode()
            .strip()
        )
        har_file = mitm_file.with_suffix(".har")
        cmd = [
            "mitmdump",
            "-nr",
            str(mitm_file),
            "-s",
            savehar_path,
            "--set",
            f"hardump={har_file}",
            "--set",
            "console_eventlog_verbosity=debug",
        ]
        if self.verbose.general:
            log.print_normal(f"Converting to HAR: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        log.print_ok(f"HAR file created: {har_file}")
        return har_file

    def extract_requests_from_har(self, har_file: Path, url_pattern: str) -> List[Dict[str, Any]]:
        """Extract requests from HAR file matching a URL pattern."""
        with open(har_file, "r", encoding="utf-8") as f:
            har_data = json.load(f)
        matches = []
        for entry in har_data.get("log", {}).get("entries", []):
            url = entry.get("request", {}).get("url", "")
            if url_pattern in url:
                matches.append(entry)
        if self.verbose.general:
            log.print_normal(
                f"Found {len(matches)} requests matching '{url_pattern}' in {har_file}"
            )
        return matches

    def extract_headers_and_cookies(
        self, har_entry: Dict[str, Any], preserve_all: bool = False
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Extract headers and cookies from a HAR entry."""
        request = har_entry.get("request", {})
        headers = {}
        for header in request.get("headers", []):
            name = header.get("name", "").lower()
            value = header.get("value", "")
            if not preserve_all and name in ["host", "content-length", "connection"]:
                continue
            headers[name] = value
        cookies = {}
        for cookie in request.get("cookies", []):
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            if name and value:
                cookies[name] = value
        cookie_header = headers.get("cookie", "")
        if cookie_header:
            for cookie_pair in cookie_header.split(";"):
                if "=" in cookie_pair:
                    name, value = cookie_pair.strip().split("=", 1)
                    cookies[name] = value
        if self.verbose.general:
            log.print_normal(f"Extracted {len(headers)} headers and {len(cookies)} cookies")
        return headers, cookies

    def extract_har_from_capture(self) -> Optional[Path]:
        """Extract HAR from the current capture file."""
        if not self.capture_file or not self.capture_file.exists():
            log.print_fail("No capture file found")
            return None

        try:
            har_file = self.convert_to_har(self.capture_file)
            return har_file
        except Exception as e:  # pylint: disable=broad-exception-caught
            log.print_fail(f"Failed to convert capture to HAR: {e}")
            return None

    def find_request_by_url_path(self, har_file: Path, url_path: str) -> Optional[Dict[str, Any]]:
        """Find request by URL path in HAR file."""
        requests = self.extract_requests_from_har(har_file, url_path)
        if not requests:
            return None

        # If multiple requests match, prioritize ones with authorization headers
        if len(requests) > 1:
            for req in requests:
                headers = req.get("request", {}).get("headers", [])
                for header in headers:
                    if header.get("name", "").lower() == "authorization":
                        return req  # Return the first request with authorization header

        return requests[0]  # Return first match if no authorization headers found

    def get_latest_captured_data(self) -> Optional[Tuple[Dict[str, str], Dict[str, str]]]:
        """Get the most recent captured data."""
        if not self.capture_dir:
            return None

        try:
            extracted_files = list(self.capture_dir.glob("extracted_data_*.json"))
            if not extracted_files:
                return None

            # Get the most recent file
            latest_file = max(extracted_files, key=lambda f: f.stat().st_mtime)
            return self.load_captured_data(latest_file)
        except Exception:  # pylint: disable=broad-exception-caught
            return None

    def load_captured_data(
        self, file_path: Path
    ) -> Optional[Tuple[Dict[str, str], Dict[str, str]]]:
        """Load captured data from a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            headers = data.get("headers", {})
            cookies = data.get("cookies", {})
            return headers, cookies
        except Exception as e:  # pylint: disable=broad-exception-caught
            log.print_fail(f"Failed to load captured data from {file_path}: {e}")
            return None
