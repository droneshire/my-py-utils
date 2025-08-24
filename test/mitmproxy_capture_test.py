"""
Tests for the mitmproxy capture functionality.
"""

import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from ryutils.mitmproxy_capture import MitmproxyCapture
from ryutils.verbose import Verbose


class TestMitmproxyCapture(unittest.TestCase):
    """Test cases for MitmproxyCapture class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.verbose = Verbose()
        self.temp_dir = tempfile.mkdtemp()
        self.capture = MitmproxyCapture(
            port=8080, verbose=self.verbose, capture_dir=Path(self.temp_dir)
        )

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self) -> None:
        """Test initialization."""
        self.assertEqual(self.capture.verbose, self.verbose)
        self.assertEqual(self.capture.capture_dir, Path(self.temp_dir))
        self.assertEqual(self.capture.port, 8080)
        self.assertIsNone(self.capture.process)
        self.assertIsNotNone(self.capture.capture_file)

    def test_extract_headers_and_cookies(self) -> None:
        """Test header and cookie extraction from HAR entry."""
        # Sample HAR entry
        har_entry: dict[str, Any] = {
            "request": {
                "headers": [
                    {"name": "authorization", "value": "Bearer token123"},
                    {"name": "content-type", "value": "application/json"},
                    {"name": "cookie", "value": "session=abc123; csrf=xyz789"},
                    {"name": "host", "value": "www.upwork.com"},
                ],
                "cookies": [
                    {"name": "session", "value": "abc123"},
                    {"name": "csrf", "value": "xyz789"},
                ],
            }
        }

        headers, cookies = self.capture.extract_headers_and_cookies(har_entry)

        # Check headers (should exclude 'host')
        self.assertIn("authorization", headers)
        self.assertIn("content-type", headers)
        self.assertIn("cookie", headers)
        self.assertNotIn("host", headers)  # Should be excluded
        self.assertEqual(headers["authorization"], "Bearer token123")

        # Check cookies
        self.assertIn("session", cookies)
        self.assertIn("csrf", cookies)
        self.assertEqual(cookies["session"], "abc123")
        self.assertEqual(cookies["csrf"], "xyz789")

    def test_find_request_by_url_path(self) -> None:
        """Test finding requests by URL path in HAR data."""
        # Create a temporary HAR file
        har_data: dict[str, Any] = {
            "log": {
                "entries": [
                    {
                        "request": {
                            "url": "https://www.upwork.com/api/graphql/v1?alias=fetchWorkHistory"
                        }
                    },
                    {"request": {"url": "https://www.upwork.com/api/graphql/v1?alias=otherQuery"}},
                ]
            }
        }

        har_file = Path(self.temp_dir) / "test.har"
        with open(har_file, "w", encoding="utf-8") as f:
            json.dump(har_data, f)

        # Test finding the request
        result = self.capture.find_request_by_url_path(har_file, "api/graphql/v1")
        self.assertIsNotNone(result)
        if result is not None:
            self.assertIn("api/graphql/v1", result["request"]["url"])

    def test_load_captured_data(self) -> None:
        """Test loading captured data from file."""
        # Create test data file
        test_data: dict[str, Any] = {
            "headers": {"authorization": "Bearer test123"},
            "cookies": {"session": "test456"},
            "timestamp": 1234567890,
        }

        data_file = Path(self.temp_dir) / "test_data.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        # Test loading
        result = self.capture.load_captured_data(data_file)
        self.assertIsNotNone(result)
        if result is not None:
            headers, cookies = result
            self.assertEqual(headers["authorization"], "Bearer test123")
            self.assertEqual(cookies["session"], "test456")

    def test_get_latest_captured_data(self) -> None:
        """Test getting the latest captured data file."""
        # Create multiple test files with different timestamps
        for i in range(3):
            test_data: dict[str, Any] = {
                "headers": {"authorization": f"Bearer test{i}"},
                "cookies": {"session": f"test{i}"},
                "timestamp": 1234567890 + i,
            }
            data_file = Path(self.temp_dir) / f"extracted_data_{i}.json"
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)
            # Ensure files have different modification times

            time.sleep(0.1)

        # Test getting latest
        result = self.capture.get_latest_captured_data()
        self.assertIsNotNone(result)
        if result is not None:
            headers, _ = result
            # Should get the last one created (highest timestamp)
            self.assertEqual(headers["authorization"], "Bearer test2")

    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_start_proxy_success(self, mock_popen: Mock, _: Mock) -> None:
        """Test successful proxy start."""
        # Mock successful process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process

        self.capture.start_proxy()

        self.assertIsNotNone(self.capture.process)
        self.assertIsNotNone(self.capture.capture_file)
        mock_popen.assert_called_once()

    @patch("subprocess.run")
    @patch("subprocess.Popen")
    def test_start_proxy_failure(self, mock_popen: Mock, _: Mock) -> None:
        """Test proxy start failure."""
        # Mock failed process
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process failed
        mock_process.communicate.return_value = ("", "Error message")
        mock_popen.return_value = mock_process

        with self.assertRaises(RuntimeError) as context:
            self.capture.start_proxy()
        self.assertIn("Mitmproxy failed to start", str(context.exception))

    @patch("subprocess.Popen")
    def test_stop_proxy(self, mock_popen: Mock) -> None:
        """Test proxy stop."""
        # Mock running process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        self.capture.process = mock_process
        self.capture.stop_proxy()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)

    def test_extract_har_from_capture_no_file(self) -> None:
        """Test HAR extraction when no capture file exists."""
        result = self.capture.extract_har_from_capture()
        self.assertIsNone(result)

    @patch("subprocess.check_output")
    @patch("subprocess.run")
    def test_extract_har_from_capture_success(
        self, mock_run: Mock, mock_check_output: Mock
    ) -> None:
        """Test successful HAR extraction."""
        # Create a mock capture file
        capture_file = Path(self.temp_dir) / "test.mitm"
        capture_file.touch()
        self.capture.capture_file = capture_file

        # Mock subprocess.check_output for savehar path
        mock_check_output.return_value = b"/path/to/savehar.py"

        # Mock successful subprocess run
        mock_run.return_value = Mock(returncode=0, stdout="Success")

        result = self.capture.extract_har_from_capture()
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result.suffix, ".har")
        mock_run.assert_called_once()

    @patch("subprocess.check_output")
    @patch("subprocess.run")
    def test_extract_har_from_capture_failure(
        self, mock_run: Mock, mock_check_output: Mock
    ) -> None:
        """Test HAR extraction failure."""
        # Create a mock capture file
        capture_file = Path(self.temp_dir) / "test.mitm"
        capture_file.touch()
        self.capture.capture_file = capture_file

        # Mock subprocess.check_output for savehar path
        mock_check_output.return_value = b"/path/to/savehar.py"

        # Mock failed subprocess run
        mock_run.side_effect = Exception("Command failed")

        result = self.capture.extract_har_from_capture()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
