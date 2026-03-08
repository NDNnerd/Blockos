"""
blockos.scraping
~~~~~~~~~~~~~~~~

Building blocks for web-scraping projects.

Provides ``BaseScraper``, a ready-to-subclass class that wraps
``requests.Session`` with common patterns:

- Per-request rate-limiting (configurable delay between calls)
- Automatic retry with exponential back-off
- URL normalisation helpers
- Response validation helpers
"""

import logging
import time
import urllib.parse
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Raised when a scraping operation cannot be completed."""


class BaseScraper:
    """Base class for web scrapers.

    Subclass this and override :meth:`scrape` to implement your own scraper.

    Parameters
    ----------
    delay:
        Minimum number of seconds to wait between consecutive requests.
        Defaults to ``1.0``.
    retries:
        Number of times to retry a failed request before raising.
        Defaults to ``3``.
    backoff_factor:
        Multiplier applied to the delay after each failed retry attempt.
        Defaults to ``0.5`` (i.e. 0.5 s, 1 s, 2 s, …).
    timeout:
        Default request timeout in seconds. Defaults to ``10``.
    headers:
        Extra HTTP headers merged into every request.

    Examples
    --------
    >>> class MyScraper(BaseScraper):
    ...     def scrape(self, url: str) -> dict:
    ...         response = self.get(url)
    ...         return {"url": url, "status": response.status_code}
    """

    DEFAULT_HEADERS: dict[str, str] = {
        "User-Agent": "Blockos/0.1 (https://github.com/NDNnerd/Blockos)"
    }

    def __init__(
        self,
        delay: float = 1.0,
        retries: int = 3,
        backoff_factor: float = 0.5,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.delay = delay
        self.timeout = timeout
        self._last_request_time: float = 0.0

        self.session = requests.Session()

        # Merge default + caller-supplied headers
        merged_headers = dict(self.DEFAULT_HEADERS)
        if headers:
            merged_headers.update(headers)
        self.session.headers.update(merged_headers)

        # Mount retry adapter for http:// and https://
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "HEAD"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    # ------------------------------------------------------------------
    # Public HTTP helpers
    # ------------------------------------------------------------------

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """Perform a rate-limited GET request.

        Parameters
        ----------
        url:
            The URL to fetch.
        **kwargs:
            Additional keyword arguments forwarded to :meth:`requests.Session.get`.

        Returns
        -------
        requests.Response

        Raises
        ------
        ScraperError
            If the response status indicates an error and *raise_for_status* is
            not overridden to ``False``.
        """
        self._enforce_rate_limit()
        kwargs.setdefault("timeout", self.timeout)
        logger.debug("GET %s", url)
        response = self.session.get(url, **kwargs)
        self._last_request_time = time.monotonic()
        self.validate_response(response)
        return response

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        """Perform a rate-limited POST request.

        Parameters
        ----------
        url:
            The URL to POST to.
        **kwargs:
            Additional keyword arguments forwarded to :meth:`requests.Session.post`.

        Returns
        -------
        requests.Response
        """
        self._enforce_rate_limit()
        kwargs.setdefault("timeout", self.timeout)
        logger.debug("POST %s", url)
        response = self.session.post(url, **kwargs)
        self._last_request_time = time.monotonic()
        self.validate_response(response)
        return response

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_response(self, response: requests.Response) -> None:
        """Validate a response object.

        The default implementation raises :exc:`ScraperError` for 4xx/5xx
        status codes.  Override this method to customise validation logic.

        Parameters
        ----------
        response:
            The response to validate.

        Raises
        ------
        ScraperError
            If the response has an HTTP error status code.
        """
        if response.status_code >= 400:
            raise ScraperError(
                f"HTTP {response.status_code} for URL: {response.url}"
            )

    # ------------------------------------------------------------------
    # URL utilities
    # ------------------------------------------------------------------

    @staticmethod
    def build_url(base: str, path: str = "", params: dict[str, Any] | None = None) -> str:
        """Build a full URL from a base URL, an optional path, and query parameters.

        Parameters
        ----------
        base:
            The base URL (e.g. ``"https://example.com"``).
        path:
            An optional path to append (e.g. ``"/search"``).
        params:
            A mapping of query-string parameters.

        Returns
        -------
        str
            The fully constructed URL.

        Examples
        --------
        >>> BaseScraper.build_url("https://example.com", "/search", {"q": "python"})
        'https://example.com/search?q=python'
        """
        url = urllib.parse.urljoin(base, path)
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        return url

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Return ``True`` if *url* is an absolute HTTP/HTTPS URL.

        Parameters
        ----------
        url:
            The string to validate.

        Examples
        --------
        >>> BaseScraper.is_valid_url("https://example.com")
        True
        >>> BaseScraper.is_valid_url("not-a-url")
        False
        """
        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except ValueError:
            return False

    @staticmethod
    def extract_domain(url: str) -> str:
        """Return the network location (domain) portion of a URL.

        Parameters
        ----------
        url:
            Any URL string.

        Examples
        --------
        >>> BaseScraper.extract_domain("https://example.com/path?q=1")
        'example.com'
        """
        return urllib.parse.urlparse(url).netloc

    # ------------------------------------------------------------------
    # Entry point for subclasses
    # ------------------------------------------------------------------

    def scrape(self, *args: Any, **kwargs: Any) -> Any:
        """Main entry point — override in subclasses to implement scraping logic."""
        raise NotImplementedError("Subclasses must implement the scrape() method.")

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "BaseScraper":
        return self

    def __exit__(self, *_: Any) -> None:
        self.session.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enforce_rate_limit(self) -> None:
        """Sleep if necessary to honour the configured ``delay`` between requests."""
        if self._last_request_time:
            elapsed = time.monotonic() - self._last_request_time
            wait = self.delay - elapsed
            if wait > 0:
                logger.debug("Rate-limiting: sleeping %.2f s", wait)
                time.sleep(wait)
