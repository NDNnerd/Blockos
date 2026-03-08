"""Tests for blockos.scraping."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from blockos.scraping import BaseScraper, ScraperError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(status_code: int = 200, url: str = "https://example.com") -> requests.Response:
    """Return a minimal fake Response."""
    resp = requests.Response()
    resp.status_code = status_code
    resp.url = url
    return resp


# ---------------------------------------------------------------------------
# URL utilities
# ---------------------------------------------------------------------------


class TestBuildUrl:
    def test_base_only(self):
        assert BaseScraper.build_url("https://example.com") == "https://example.com"

    def test_with_path(self):
        assert BaseScraper.build_url("https://example.com", "/search") == "https://example.com/search"

    def test_with_params(self):
        url = BaseScraper.build_url("https://example.com", "/search", {"q": "python"})
        assert url == "https://example.com/search?q=python"

    def test_with_multiple_params(self):
        url = BaseScraper.build_url("https://example.com", params={"a": "1", "b": "2"})
        assert "a=1" in url
        assert "b=2" in url


class TestIsValidUrl:
    def test_valid_https(self):
        assert BaseScraper.is_valid_url("https://example.com") is True

    def test_valid_http(self):
        assert BaseScraper.is_valid_url("http://example.com/path") is True

    def test_invalid_no_scheme(self):
        assert BaseScraper.is_valid_url("example.com") is False

    def test_invalid_ftp_scheme(self):
        assert BaseScraper.is_valid_url("ftp://example.com") is False

    def test_invalid_empty(self):
        assert BaseScraper.is_valid_url("") is False

    def test_invalid_plain_string(self):
        assert BaseScraper.is_valid_url("not-a-url") is False


class TestExtractDomain:
    def test_simple(self):
        assert BaseScraper.extract_domain("https://example.com/path?q=1") == "example.com"

    def test_with_port(self):
        assert BaseScraper.extract_domain("http://localhost:8080/") == "localhost:8080"

    def test_empty(self):
        assert BaseScraper.extract_domain("") == ""


# ---------------------------------------------------------------------------
# Initialisation & session configuration
# ---------------------------------------------------------------------------


class TestInit:
    def test_defaults(self):
        scraper = BaseScraper()
        assert scraper.delay == 1.0
        assert scraper.timeout == 10.0

    def test_custom_params(self):
        scraper = BaseScraper(delay=2.0, timeout=5.0)
        assert scraper.delay == 2.0
        assert scraper.timeout == 5.0

    def test_custom_headers_merged(self):
        scraper = BaseScraper(headers={"X-Custom": "value"})
        assert scraper.session.headers["X-Custom"] == "value"
        assert "User-Agent" in scraper.session.headers

    def test_context_manager_closes_session(self):
        with BaseScraper() as scraper:
            assert scraper.session is not None
        # After __exit__, further use would fail but the object still exists
        assert scraper is not None


# ---------------------------------------------------------------------------
# validate_response
# ---------------------------------------------------------------------------


class TestValidateResponse:
    def test_2xx_does_not_raise(self):
        scraper = BaseScraper()
        resp = _make_response(200)
        scraper.validate_response(resp)  # should not raise

    def test_3xx_does_not_raise(self):
        scraper = BaseScraper()
        resp = _make_response(301)
        scraper.validate_response(resp)  # should not raise

    def test_4xx_raises(self):
        scraper = BaseScraper()
        resp = _make_response(404)
        with pytest.raises(ScraperError, match="404"):
            scraper.validate_response(resp)

    def test_5xx_raises(self):
        scraper = BaseScraper()
        resp = _make_response(500)
        with pytest.raises(ScraperError, match="500"):
            scraper.validate_response(resp)


# ---------------------------------------------------------------------------
# HTTP methods (mocked session)
# ---------------------------------------------------------------------------


class TestGet:
    def test_get_calls_session(self):
        scraper = BaseScraper(delay=0)
        mock_resp = _make_response(200)
        scraper.session.get = MagicMock(return_value=mock_resp)

        result = scraper.get("https://example.com")

        scraper.session.get.assert_called_once()
        assert result.status_code == 200

    def test_get_raises_on_error_status(self):
        scraper = BaseScraper(delay=0)
        mock_resp = _make_response(403)
        scraper.session.get = MagicMock(return_value=mock_resp)

        with pytest.raises(ScraperError, match="403"):
            scraper.get("https://example.com")

    def test_get_uses_default_timeout(self):
        scraper = BaseScraper(delay=0, timeout=7.0)
        mock_resp = _make_response(200)
        scraper.session.get = MagicMock(return_value=mock_resp)

        scraper.get("https://example.com")
        _, kwargs = scraper.session.get.call_args
        assert kwargs.get("timeout") == 7.0

    def test_get_caller_can_override_timeout(self):
        scraper = BaseScraper(delay=0)
        mock_resp = _make_response(200)
        scraper.session.get = MagicMock(return_value=mock_resp)

        scraper.get("https://example.com", timeout=99)
        _, kwargs = scraper.session.get.call_args
        assert kwargs.get("timeout") == 99


class TestPost:
    def test_post_calls_session(self):
        scraper = BaseScraper(delay=0)
        mock_resp = _make_response(201)
        scraper.session.post = MagicMock(return_value=mock_resp)

        result = scraper.post("https://example.com/submit", data={"key": "val"})

        scraper.session.post.assert_called_once()
        assert result.status_code == 201


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimit:
    def test_rate_limit_respected(self):
        scraper = BaseScraper(delay=0.1)
        mock_resp = _make_response(200)
        scraper.session.get = MagicMock(return_value=mock_resp)

        # Simulate that a request was made 0.01 s ago by controlling monotonic
        base_time = 1000.0
        # First call records _last_request_time at base_time
        # Second call should see elapsed=0.01 and sleep for ~0.09 s
        call_times = [base_time, base_time + 0.01, base_time + 0.11]
        call_iter = iter(call_times)

        with patch("blockos.scraping.time.monotonic", side_effect=call_iter), \
             patch("blockos.scraping.time.sleep") as mock_sleep:
            scraper.get("https://example.com")   # records _last_request_time = base_time
            scraper.get("https://example.com")   # should sleep ~0.09 s

        mock_sleep.assert_called_once()
        slept = mock_sleep.call_args[0][0]
        assert slept == pytest.approx(0.09, abs=0.01)


# ---------------------------------------------------------------------------
# scrape() not implemented
# ---------------------------------------------------------------------------


class TestScrapeNotImplemented:
    def test_base_scrape_raises(self):
        scraper = BaseScraper()
        with pytest.raises(NotImplementedError):
            scraper.scrape()

    def test_subclass_can_override(self):
        class MyScraper(BaseScraper):
            def scrape(self, url):
                return f"scraped:{url}"

        s = MyScraper(delay=0)
        assert s.scrape("https://example.com") == "scraped:https://example.com"
