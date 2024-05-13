"""
Get proxies from various sources.
"""

import typing as T

from fp.fp import FreeProxy

from ryutils import log


class Proxies:
    def get(
        self, verbose: bool = False, kwargs: T.Optional[T.Dict[str, T.Any]] = None
    ) -> T.Dict[str, str]:
        raise NotImplementedError


class ScrapeDogProxy(Proxies):
    """_summary_
    https://api.scrapingdog.com/
    """

    def __init__(self, api_key: T.Optional[str] = None):
        assert api_key is not None, "Missing SCRAPER_DOG_PROXY_API_KEY in .env"
        self.proxy_url = {
            "http": f"http://scrapingdog:{api_key}@proxy.scrapingdog.com:8081",
            "https": f"http://scrapingdog:{api_key}@proxy.scrapingdog.com:8081",
        }

    def get(self, verbose: bool = False, kwargs: T.Optional[T.Dict[str, T.Any]] = None):
        if verbose:
            log.print_bright(f"Using proxy: {self.proxy_url}")
        return self.proxy_url


class FreeProxyProxy(Proxies):
    """
    https://pypi.org/project/free-proxy/
    """

    def get(
        self, verbose: bool = False, kwargs: T.Optional[T.Dict[str, T.Any]] = None
    ) -> T.Dict[str, str]:
        if kwargs is None:
            kwargs = {
                "country_id": ["US"],
                "rand": True,
            }

        kwargs["https"] = False
        https_kwargs = kwargs.copy()
        https_kwargs["https"] = True

        proxy = {
            "http": FreeProxy(**kwargs).get(),
            "https": FreeProxy(**https_kwargs).get(),
        }
        if verbose:
            log.print_bright(f"Using proxy: {proxy}")
        return proxy
