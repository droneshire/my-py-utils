import typing as T
import urllib.parse

import requests

from ryutils import log, wait

MY_IP_URL = "http://icanhazip.com/"


def create_websocket_url(base_url: str, params: T.Dict[str, T.Any]) -> str:
    """
    Constructs a WebSocket URL with given parameters.
    """
    url_parts = list(urllib.parse.urlparse(base_url))
    query = dict(urllib.parse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib.parse.urlencode(query)
    return urllib.parse.urlunparse(url_parts)


class Web2Client:
    def __init__(
        self,
        base_url: str = "",
        rate_limit_delay: float = 5.0,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        self.dry_run = dry_run
        self.base_url = base_url
        self.rate_limit_delay = rate_limit_delay
        self.verbose = verbose

        if dry_run:
            log.print_warn("Web2Client in dry run mode...")

        self.requests = requests

    def _get_request(
        self,
        url: str,
        headers: T.Optional[T.Dict[str, T.Any]] = None,
        params: T.Optional[T.Dict[str, T.Any]] = None,
        timeout: float = 5.0,
    ) -> T.Any:
        if self.rate_limit_delay > 0.0:
            wait.wait(self.rate_limit_delay)

        try:
            return self.requests.request(
                "GET", url, params=params, headers=headers, timeout=timeout
            ).json()
        except KeyboardInterrupt:
            raise
        except:  # pylint: disable=bare-except
            return {}

    def _post_request(
        self,
        url: str,
        json_data: T.Optional[T.Dict[str, T.Any]] = None,
        headers: T.Optional[T.Dict[str, T.Any]] = None,
        params: T.Optional[T.Dict[str, T.Any]] = None,
        timeout: float = 5.0,
        delay: float = 5.0,
    ) -> T.Any:
        if self.dry_run:
            return {}

        if delay > 0.0:
            wait.wait(delay)

        try:
            return self.requests.request(
                "POST",
                url,
                json=json_data,
                params=params,
                headers=headers,
                timeout=timeout,
            ).json()
        except KeyboardInterrupt:
            raise
        except:  # pylint: disable=bare-except
            log.format_fail(f"Failed to post to {url}")
            return {}

    def url_download(
        self,
        url: str,
        file_path: str,
        data: T.Optional[str] = None,
        headers: T.Optional[T.Dict[str, T.Any]] = None,
        params: T.Optional[T.Dict[str, T.Any]] = None,
        cookies: T.Optional[T.Dict[str, T.Any]] = None,
        timeout: float = 5.0,
    ) -> None:
        if self.dry_run:
            return

        try:
            with self.requests.request(
                "GET",
                url,
                data=data,
                params=params,
                headers=headers,
                cookies=cookies,
                timeout=timeout,
                stream=True,
                allow_redirects=True,
            ) as r:
                r.raise_for_status()
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except KeyboardInterrupt as exc:
            raise exc
        except Exception as exc:  # pylint: disable=broad-except
            log.format_fail(f"Failed to download {url} to {file_path}: {exc}")
            return
