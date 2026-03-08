# Blockos
Off-Brand Building Blocks for Basic Python Projects

Blockos is a lightweight Python module that provides reusable base classes and
helpers for scaffolding web-scraping and data-cleaning projects.

---

## Installation

```bash
pip install -e .
```

For development (includes `pytest`):

```bash
pip install -e ".[dev]"
```

---

## Modules

### `blockos.scraping` — Web-scraping building blocks

`BaseScraper` is a ready-to-subclass class wrapping `requests.Session` with:

| Feature | Details |
|---|---|
| Rate limiting | Configurable minimum delay between requests |
| Automatic retries | Exponential back-off on 429/5xx responses |
| URL utilities | `build_url`, `is_valid_url`, `extract_domain` |
| Response validation | Raises `ScraperError` on 4xx/5xx by default |
| Context-manager support | Closes the session on exit |

**Quick start**

```python
from blockos.scraping import BaseScraper

class ProductScraper(BaseScraper):
    def scrape(self, url: str) -> dict:
        response = self.get(url)
        return {"url": url, "html_length": len(response.text)}

with ProductScraper(delay=1.5) as scraper:
    data = scraper.scrape("https://example.com")
```

**URL helpers**

```python
BaseScraper.build_url("https://example.com", "/search", {"q": "python"})
# → 'https://example.com/search?q=python'

BaseScraper.is_valid_url("https://example.com")   # → True
BaseScraper.is_valid_url("not-a-url")              # → False

BaseScraper.extract_domain("https://example.com/path")  # → 'example.com'
```

---

### `blockos.cleaning` — Data-cleaning building blocks

`DataCleaner` provides stateless helpers for common cleaning tasks:

| Method | Description |
|---|---|
| `clean_string` | Strip, collapse whitespace, optionally lower-case |
| `normalize_whitespace` | Collapse all whitespace runs to a single space |
| `remove_special_characters` | Keep only alphanumerics (configurable) |
| `normalize_unicode` | NFC/NFKC/NFD/NFKD normalisation |
| `to_int` / `to_float` | Safe numeric conversion with a fallback default |
| `to_bool` | Handles `"true"`, `"yes"`, `"1"`, `"on"`, … |
| `to_datetime` | Parses common date/time formats automatically |
| `is_empty` | Detects `None`, blank strings, `"N/A"`, `"null"`, … |
| `fill_missing` | Replace empty values with a fill value |
| `drop_empty_keys` | Remove empty-valued keys from a dict |
| `deduplicate` | Remove duplicates while preserving insertion order |
| `clean_records` | Apply per-field cleaners to a list of dicts |

**Quick start**

```python
from blockos.cleaning import DataCleaner

cleaner = DataCleaner()

# Individual value cleaning
cleaner.clean_string("  Hello, World!  ")   # → 'Hello, World!'
cleaner.to_int("42")                         # → 42
cleaner.to_float("1,234.56")                 # → 1234.56
cleaner.to_bool("yes")                       # → True
cleaner.to_datetime("2024-06-15")            # → datetime(2024, 6, 15)

# Batch record cleaning
records = [
    {"name": "  Alice ", "age": "30", "score": "N/A"},
    {"name": "bob",      "age": "25", "score": "95.5"},
]

cleaned = cleaner.clean_records(
    records,
    field_cleaners={
        "name":  cleaner.clean_string,
        "age":   cleaner.to_int,
        "score": cleaner.to_float,
    },
    drop_empty=True,
)
# → [{'name': 'Alice', 'age': 30}, {'name': 'bob', 'age': 25, 'score': 95.5}]
```

---

## Running tests

```bash
pytest
```

---

## License

See [LICENSE](LICENSE).
