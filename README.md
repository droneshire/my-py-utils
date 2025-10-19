# My Common Python Utils

[![Python application](https://github.com/droneshire/my-py-utils/actions/workflows/python-app.yml/badge.svg)](https://github.com/droneshire/my-py-utils/actions/workflows/python-app.yml)
[![Upload Python Package](https://github.com/droneshire/my-py-utils/actions/workflows/python-publish.yml/badge.svg)](https://github.com/droneshire/my-py-utils/actions/workflows/python-publish.yml)

A comprehensive collection of Python utilities built over time for various projects. This library provides essential tools for HTTP requests, caching, logging, system monitoring, alerts, and more.

## Installation

```bash
pip install ryutils
```

## Features

### 🌐 HTTP Requests & Caching

- **`RequestsHelper`** - Advanced HTTP client with retry logic, caching, and comprehensive logging
- **`JsonCache`** - Lightweight JSON-based cache with expiration support
- **Request caching** - Automatic caching of GET requests with configurable expiration
- **Retry strategies** - Exponential backoff for failed requests
- **Request logging** - Comprehensive logging of all HTTP requests and responses

### 📊 System Monitoring & Profiling

- **`ResourceProfiler`** - CPU and memory usage profiling decorator
- **System stats** - Real-time system resource monitoring
- **Performance tracking** - Function execution time and resource consumption

### 📝 Logging & Output

- **`log`** - Advanced logging system with colored output and multiple handlers
- **Multi-threaded logging** - Per-thread log files with configurable prefixes
- **Verbose output** - Configurable verbosity levels for different components
- **CSV logging** - Structured logging to CSV files

### 🚨 Alerting System

- **Slack alerts** - Send notifications to Slack channels
- **Discord alerts** - Send notifications to Discord webhooks
- **Mock alerts** - Testing and development alert system
- **Alert factory** - Unified interface for different alert types

### 📱 SMS & Communication

- **TextBelt SMS** - Send SMS messages via TextBelt API
- **Multi-region support** - US, Canada, and international SMS support

### 🔧 Utilities

- **Dictionary utilities** - Advanced dictionary manipulation and comparison
- **Path utilities** - File and directory path helpers
- **URL shortening** - TinyURL integration for URL shortening
- **Text processing** - Text chunk reading and processing utilities
- **Format utilities** - Data formatting and conversion helpers

### 🔒 Security & Networking

- **SSH tunneling** - Modern SSH tunnel implementation using paramiko
- **Proxy capture** - Mitmproxy integration for request/response capture
- **Header extraction** - Extract headers and cookies from captured requests

### 🧵 Concurrency

- **Worker threads** - Queue-based worker thread implementation
- **Thread-safe operations** - Thread-safe caching and logging

## Quick Start

### HTTP Requests with Caching

```python
from ryutils.requests_helper import RequestsHelper
from ryutils.verbose import Verbose

# Create a requests helper with caching
helper = RequestsHelper(
    base_url="https://api.example.com",
    verbose=Verbose(),
    cache_expiry_seconds=3600,  # 1 hour cache
    cache_file=Path("cache.json")
)

# GET request (automatically cached)
data = helper.get("/users", {"page": 1})

# POST request (clears cache for the endpoint)
result = helper.post("/users", {"name": "John"})
```

### System Resource Profiling

```python
from ryutils.system_stats import profile_function

@profile_function
def my_function():
    # Your code here
    return "result"

# Function execution will be automatically profiled
result = my_function()
```

### Alerting

```python
from ryutils.alerts.factory import AlertFactory
from ryutils.alerts.alert_types import AlertType

# Create alert factory
factory = AlertFactory()

# Send Slack alert
factory.send_alert(
    AlertType.SLACK,
    message="System is running smoothly",
    webhook_url="https://hooks.slack.com/..."
)

# Send Discord alert
factory.send_alert(
    AlertType.DISCORD,
    message="Deployment completed",
    webhook_url="https://discord.com/api/webhooks/..."
)
```

### Logging

```python
from ryutils import log

# Setup logging
log.setup(
    log_dir="./logs",
    log_level="INFO",
    main_thread_name="main"
)

# Use colored logging
log.print_ok("Success message")
log.print_warn("Warning message")
log.print_fail("Error message")
log.print_bright("Info message")
```

### Dictionary Utilities

```python
from ryutils.dict_util import (
    check_dict_keys_recursive,
    patch_missing_keys_recursive,
    flatten_dict,
    safe_get
)

# Check for missing keys recursively
missing = check_dict_keys_recursive(template_dict, data_dict)

# Patch missing keys
patched = patch_missing_keys_recursive(template_dict, data_dict)

# Flatten nested dictionary
flat = flatten_dict(nested_dict)

# Safe dictionary access
value = safe_get(data, "key.subkey", default="default")
```

### SMS Notifications

```python
from ryutils.sms.pytextbelt import Textbelt

# Create SMS client
sms = Textbelt()

# Send SMS
recipient = sms.Recipient(
    phone="+1234567890",
    key="your-textbelt-key",
    region="us"
)

sms.send(recipient, "Hello from Python!")
```

### SSH Tunneling

```python
from ryutils.modern_ssh_tunnel import ModernSSHTunnel

# Create SSH tunnel
tunnel = ModernSSHTunnel(
    ssh_host="ssh.example.com",
    ssh_port=22,
    ssh_username="user",
    ssh_pkey="path/to/private/key",
    remote_host="remote.example.com",
    remote_port=3306,
    local_port=13306
)

# Start tunnel
tunnel.start()

# Use tunnel (e.g., connect to remote database on localhost:13306)
# ... your code ...

# Stop tunnel
tunnel.stop()
```

## Configuration

### Verbose Configuration

```python
from ryutils.verbose import Verbose

verbose = Verbose(
    requests=True,           # Log HTTP requests
    requests_url=True,      # Log request URLs
    requests_response=True, # Log responses
    request_cache=True,     # Log cache operations
    alerts=True             # Log alert operations
)
```

### Cache Configuration

```python
from ryutils.json_cache import JsonCache

cache = JsonCache(
    cache_file=Path("cache.json"),
    expiry_seconds=3600,    # 1 hour expiration
    verbose=Verbose()
)
```

## Dependencies

The library uses minimal external dependencies:

- `requests` - HTTP requests
- `paramiko` - SSH tunneling
- `psutil` - System monitoring
- `memory-profiler` - Memory profiling
- `pyshorteners` - URL shortening
- `slack-sdk` - Slack integration
- `discord-webhook` - Discord integration
- `pytz` - Timezone handling

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/droneshire/my-py-utils.git
cd my-py-utils

# Create virtual environment
make init

# Install development dependencies
make install_dev

# Run tests
make test

# Run linting
make lint
```

### Available Make Commands

- `make init` - Initialize virtual environment
- `make install` - Install production dependencies
- `make install_dev` - Install development dependencies
- `make test` - Run all tests
- `make lint` - Run linting (black, mypy, pylint)
- `make format` - Format code with black and isort
- `make clean` - Clean up temporary files

## Testing

The library includes comprehensive tests for all major components:

```bash
# Run all tests
make test

# Run specific test module
make test TESTMODULE=dict_util_test
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions, issues, or contributions, please use the [GitHub Issues](https://github.com/droneshire/my-py-utils/issues) page.
