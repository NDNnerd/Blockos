"""
blockos.cleaning
~~~~~~~~~~~~~~~~

Building blocks for data-cleaning projects.

Provides ``DataCleaner``, a stateless utility class whose methods can be used
directly or after subclassing to build domain-specific cleaning pipelines.

Typical usage::

    from blockos.cleaning import DataCleaner

    cleaner = DataCleaner()

    # Clean an individual value
    cleaned = cleaner.clean_string("  Hello, World!  ")

    # Clean a list of records (list of dicts)
    records = [{"name": "  Alice ", "age": "30"}, {"name": "bob", "age": None}]
    cleaned_records = cleaner.clean_records(records, {
        "name": cleaner.clean_string,
        "age": cleaner.to_int,
    })
"""

import logging
import re
import unicodedata
from datetime import datetime
from typing import Any, Callable, Iterable

logger = logging.getLogger(__name__)


class CleaningError(Exception):
    """Raised when a cleaning operation cannot be completed."""


class DataCleaner:
    """Utility class with helpers for common data-cleaning tasks.

    All methods are instance methods for easy subclassing, but none of them
    depend on instance state — they can also be used as plain functions by
    calling them on a shared instance.

    Examples
    --------
    >>> cleaner = DataCleaner()
    >>> cleaner.clean_string("  hello  ")
    'hello'
    >>> cleaner.to_int("42")
    42
    >>> cleaner.to_float("3.14")
    3.14
    """

    # ------------------------------------------------------------------
    # String cleaning
    # ------------------------------------------------------------------

    def clean_string(
        self,
        value: Any,
        *,
        lowercase: bool = False,
        strip_chars: str | None = None,
    ) -> str | None:
        """Normalise a string value.

        - Converts *value* to ``str`` (unless it is ``None`` / empty, in which
          case ``None`` is returned).
        - Strips leading/trailing whitespace (or *strip_chars* if given).
        - Collapses internal runs of whitespace to a single space.

        Parameters
        ----------
        value:
            The value to clean.
        lowercase:
            If ``True``, convert the result to lower-case.
        strip_chars:
            Characters to strip instead of whitespace.

        Returns
        -------
        str or None
        """
        if value is None:
            return None
        text = str(value)
        text = text.strip(strip_chars) if strip_chars is not None else text.strip()
        text = re.sub(r"\s+", " ", text)
        if not text:
            return None
        if lowercase:
            text = text.lower()
        return text

    def normalize_whitespace(self, value: str) -> str:
        """Replace any sequence of whitespace characters with a single space and strip.

        Parameters
        ----------
        value:
            Input string.

        Returns
        -------
        str
        """
        return re.sub(r"\s+", " ", value).strip()

    def remove_special_characters(
        self, value: str, *, allow_chars: str = r"a-zA-Z0-9\s"
    ) -> str:
        """Remove characters not present in the *allow_chars* character class.

        Parameters
        ----------
        value:
            Input string.
        allow_chars:
            The **contents** of a regex character class specifying which
            characters to keep.  Do **not** wrap the value in ``[…]`` — that
            is done internally.  Defaults to ``r"a-zA-Z0-9\\s"`` (alphanumerics
            and whitespace).

        Returns
        -------
        str

        Examples
        --------
        >>> DataCleaner().remove_special_characters("hello, world!")
        'hello world'
        >>> DataCleaner().remove_special_characters("abc-123", allow_chars=r"a-z0-9\\-")
        'abc-123'
        """
        return re.sub(f"[^{allow_chars}]", "", value)

    def normalize_unicode(self, value: str, form: str = "NFC") -> str:
        """Normalise Unicode in *value* using the specified *form*.

        Parameters
        ----------
        value:
            Input string.
        form:
            Unicode normalisation form: ``"NFC"``, ``"NFKC"``, ``"NFD"``,
            or ``"NFKD"``.  Defaults to ``"NFC"``.

        Returns
        -------
        str
        """
        return unicodedata.normalize(form, value)

    # ------------------------------------------------------------------
    # Type conversions
    # ------------------------------------------------------------------

    def to_int(self, value: Any, default: int | None = None) -> int | None:
        """Convert *value* to ``int``, returning *default* on failure.

        Parameters
        ----------
        value:
            The value to convert.
        default:
            Value to return when conversion fails.  Defaults to ``None``.

        Returns
        -------
        int or None
        """
        if value is None:
            return default
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            logger.debug("to_int: could not convert %r", value)
            return default

    def to_float(self, value: Any, default: float | None = None) -> float | None:
        """Convert *value* to ``float``, returning *default* on failure.

        Parameters
        ----------
        value:
            The value to convert.
        default:
            Value to return when conversion fails.  Defaults to ``None``.

        Returns
        -------
        float or None
        """
        if value is None:
            return default
        try:
            # Remove common formatting characters before conversion
            cleaned = re.sub(r"[,\s]", "", str(value).strip())
            return float(cleaned)
        except (ValueError, TypeError):
            logger.debug("to_float: could not convert %r", value)
            return default

    def to_bool(self, value: Any, default: bool | None = None) -> bool | None:
        """Convert a loosely-typed boolean representation to ``bool``.

        Truthy strings: ``"true"``, ``"yes"``, ``"1"``, ``"on"``
        Falsy strings:  ``"false"``, ``"no"``, ``"0"``, ``"off"``

        Parameters
        ----------
        value:
            The value to convert.
        default:
            Value to return when conversion fails.  Defaults to ``None``.

        Returns
        -------
        bool or None
        """
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        text = str(value).strip().lower()
        if text in ("true", "yes", "1", "on"):
            return True
        if text in ("false", "no", "0", "off"):
            return False
        logger.debug("to_bool: could not convert %r", value)
        return default

    def to_datetime(
        self,
        value: Any,
        fmt: str | None = None,
        default: datetime | None = None,
    ) -> datetime | None:
        """Parse *value* into a :class:`datetime.datetime`.

        Parameters
        ----------
        value:
            The value to parse.  If it is already a :class:`~datetime.datetime`
            it is returned as-is.
        fmt:
            ``strptime`` format string.  If ``None``, a selection of common
            ISO-8601 formats is tried automatically.
        default:
            Value to return when parsing fails.  Defaults to ``None``.

        Returns
        -------
        datetime or None
        """
        if isinstance(value, datetime):
            return value
        if value is None:
            return default
        text = str(value).strip()
        if fmt:
            try:
                return datetime.strptime(text, fmt)
            except (ValueError, TypeError):
                logger.debug("to_datetime: could not parse %r with format %r", value, fmt)
                return default

        for _fmt in (
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ):
            try:
                return datetime.strptime(text, _fmt)
            except ValueError:
                continue
        logger.debug("to_datetime: could not parse %r", value)
        return default

    # ------------------------------------------------------------------
    # Missing-value handling
    # ------------------------------------------------------------------

    def is_empty(self, value: Any) -> bool:
        """Return ``True`` if *value* is considered empty.

        Empty values are: ``None``, empty strings (after stripping), empty
        sequences / mappings, and common placeholder strings such as
        ``"N/A"``, ``"null"``, ``"-"``.

        Parameters
        ----------
        value:
            The value to test.

        Returns
        -------
        bool
        """
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip().lower() in ("", "n/a", "na", "null", "none", "-", "--")
        if isinstance(value, (list, dict, set, tuple)):
            return len(value) == 0
        return False

    def fill_missing(self, value: Any, fill_value: Any = None) -> Any:
        """Return *fill_value* when *value* is empty; otherwise return *value*.

        Parameters
        ----------
        value:
            The value to check.
        fill_value:
            Replacement value.  Defaults to ``None``.

        Returns
        -------
        Any
        """
        return fill_value if self.is_empty(value) else value

    def drop_empty_keys(self, record: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of *record* with all empty-valued keys removed.

        Parameters
        ----------
        record:
            Input dictionary.

        Returns
        -------
        dict
        """
        return {k: v for k, v in record.items() if not self.is_empty(v)}

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def deduplicate(
        self,
        items: Iterable[Any],
        key: Callable[[Any], Any] | None = None,
    ) -> list[Any]:
        """Remove duplicate items while preserving insertion order.

        Parameters
        ----------
        items:
            An iterable of items to deduplicate.
        key:
            An optional callable that returns the value used for equality
            comparison.  If ``None``, the item itself is used.

        Returns
        -------
        list

        Examples
        --------
        >>> DataCleaner().deduplicate([1, 2, 1, 3, 2])
        [1, 2, 3]
        >>> DataCleaner().deduplicate(
        ...     [{"id": 1, "v": "a"}, {"id": 1, "v": "b"}, {"id": 2, "v": "c"}],
        ...     key=lambda r: r["id"],
        ... )
        [{'id': 1, 'v': 'a'}, {'id': 2, 'v': 'c'}]
        """
        seen: set[Any] = set()
        result: list[Any] = []
        for item in items:
            k = key(item) if key else item
            # Make unhashable keys hashable via repr as a fallback
            try:
                hash(k)
            except TypeError:
                k = repr(k)
            if k not in seen:
                seen.add(k)
                result.append(item)
        return result

    # ------------------------------------------------------------------
    # Batch cleaning
    # ------------------------------------------------------------------

    def clean_records(
        self,
        records: Iterable[dict[str, Any]],
        field_cleaners: dict[str, Callable[[Any], Any]],
        *,
        drop_empty: bool = False,
    ) -> list[dict[str, Any]]:
        """Apply per-field cleaning functions to a sequence of records.

        Parameters
        ----------
        records:
            An iterable of dictionaries representing data records.
        field_cleaners:
            A mapping of field name → cleaning callable.  Only fields present
            in this mapping are transformed; all others are passed through
            unchanged.
        drop_empty:
            If ``True``, call :meth:`drop_empty_keys` on each record after
            applying the cleaners.

        Returns
        -------
        list[dict]

        Examples
        --------
        >>> cleaner = DataCleaner()
        >>> records = [{"name": "  Alice ", "age": "30"}]
        >>> cleaner.clean_records(records, {"name": cleaner.clean_string, "age": cleaner.to_int})
        [{'name': 'Alice', 'age': 30}]
        """
        result: list[dict[str, Any]] = []
        for record in records:
            cleaned: dict[str, Any] = {}
            for key, value in record.items():
                cleaner_fn = field_cleaners.get(key)
                if cleaner_fn is not None:
                    try:
                        cleaned[key] = cleaner_fn(value)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Error cleaning field %r: %s", key, exc)
                        cleaned[key] = value
                else:
                    cleaned[key] = value
            if drop_empty:
                cleaned = self.drop_empty_keys(cleaned)
            result.append(cleaned)
        return result
