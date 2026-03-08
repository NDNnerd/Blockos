"""Tests for blockos.cleaning."""

from datetime import datetime

import pytest

from blockos.cleaning import DataCleaner


@pytest.fixture
def cleaner() -> DataCleaner:
    return DataCleaner()


# ---------------------------------------------------------------------------
# clean_string
# ---------------------------------------------------------------------------


class TestCleanString:
    def test_strips_whitespace(self, cleaner):
        assert cleaner.clean_string("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self, cleaner):
        assert cleaner.clean_string("hello   world") == "hello world"

    def test_none_returns_none(self, cleaner):
        assert cleaner.clean_string(None) is None

    def test_empty_string_returns_none(self, cleaner):
        assert cleaner.clean_string("   ") is None

    def test_converts_non_string(self, cleaner):
        assert cleaner.clean_string(42) == "42"

    def test_lowercase_flag(self, cleaner):
        assert cleaner.clean_string("Hello World", lowercase=True) == "hello world"

    def test_strip_chars(self, cleaner):
        assert cleaner.clean_string("***text***", strip_chars="*") == "text"


# ---------------------------------------------------------------------------
# normalize_whitespace
# ---------------------------------------------------------------------------


class TestNormalizeWhitespace:
    def test_tabs_and_newlines(self, cleaner):
        assert cleaner.normalize_whitespace("a\t\nb") == "a b"

    def test_multiple_spaces(self, cleaner):
        assert cleaner.normalize_whitespace("a   b") == "a b"

    def test_strips_ends(self, cleaner):
        assert cleaner.normalize_whitespace("  x  ") == "x"


# ---------------------------------------------------------------------------
# remove_special_characters
# ---------------------------------------------------------------------------


class TestRemoveSpecialCharacters:
    def test_removes_punctuation(self, cleaner):
        result = cleaner.remove_special_characters("hello, world!")
        assert result == "hello world"

    def test_keeps_alphanumeric(self, cleaner):
        result = cleaner.remove_special_characters("abc123")
        assert result == "abc123"

    def test_custom_allow_chars(self, cleaner):
        result = cleaner.remove_special_characters("abc-123", allow_chars=r"a-z0-9\-")
        assert result == "abc-123"


# ---------------------------------------------------------------------------
# normalize_unicode
# ---------------------------------------------------------------------------


class TestNormalizeUnicode:
    def test_nfc(self, cleaner):
        # Composed form: é (U+00E9)
        result = cleaner.normalize_unicode("\u00e9", form="NFC")
        assert result == "\u00e9"

    def test_nfkd_decomposes(self, cleaner):
        result = cleaner.normalize_unicode("\u00e9", form="NFKD")
        assert result == "e\u0301"


# ---------------------------------------------------------------------------
# to_int
# ---------------------------------------------------------------------------


class TestToInt:
    def test_valid_string(self, cleaner):
        assert cleaner.to_int("42") == 42

    def test_valid_int(self, cleaner):
        assert cleaner.to_int(10) == 10

    def test_none_returns_default(self, cleaner):
        assert cleaner.to_int(None) is None

    def test_invalid_returns_default(self, cleaner):
        assert cleaner.to_int("abc") is None

    def test_custom_default(self, cleaner):
        assert cleaner.to_int("bad", default=0) == 0

    def test_strips_whitespace(self, cleaner):
        assert cleaner.to_int(" 7 ") == 7


# ---------------------------------------------------------------------------
# to_float
# ---------------------------------------------------------------------------


class TestToFloat:
    def test_valid_string(self, cleaner):
        assert cleaner.to_float("3.14") == pytest.approx(3.14)

    def test_comma_formatted(self, cleaner):
        assert cleaner.to_float("1,234.56") == pytest.approx(1234.56)

    def test_none_returns_default(self, cleaner):
        assert cleaner.to_float(None) is None

    def test_invalid_returns_default(self, cleaner):
        assert cleaner.to_float("nope") is None

    def test_custom_default(self, cleaner):
        assert cleaner.to_float("nope", default=0.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# to_bool
# ---------------------------------------------------------------------------


class TestToBool:
    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "yes", "1", "on"])
    def test_truthy_values(self, cleaner, value):
        assert cleaner.to_bool(value) is True

    @pytest.mark.parametrize("value", ["false", "False", "FALSE", "no", "0", "off"])
    def test_falsy_values(self, cleaner, value):
        assert cleaner.to_bool(value) is False

    def test_actual_bool_true(self, cleaner):
        assert cleaner.to_bool(True) is True

    def test_actual_bool_false(self, cleaner):
        assert cleaner.to_bool(False) is False

    def test_none_returns_default(self, cleaner):
        assert cleaner.to_bool(None) is None

    def test_invalid_returns_default(self, cleaner):
        assert cleaner.to_bool("maybe", default=False) is False


# ---------------------------------------------------------------------------
# to_datetime
# ---------------------------------------------------------------------------


class TestToDatetime:
    def test_iso_date(self, cleaner):
        result = cleaner.to_datetime("2024-06-15")
        assert result == datetime(2024, 6, 15)

    def test_iso_datetime(self, cleaner):
        result = cleaner.to_datetime("2024-06-15T12:30:00")
        assert result == datetime(2024, 6, 15, 12, 30, 0)

    def test_iso_datetime_with_z(self, cleaner):
        result = cleaner.to_datetime("2024-06-15T12:30:00Z")
        assert result == datetime(2024, 6, 15, 12, 30, 0)

    def test_slash_date_dmy(self, cleaner):
        result = cleaner.to_datetime("15/06/2024")
        assert result == datetime(2024, 6, 15)

    def test_custom_format(self, cleaner):
        result = cleaner.to_datetime("Jun 15 2024", fmt="%b %d %Y")
        assert result == datetime(2024, 6, 15)

    def test_passthrough_datetime(self, cleaner):
        dt = datetime(2024, 1, 1)
        assert cleaner.to_datetime(dt) is dt

    def test_none_returns_default(self, cleaner):
        assert cleaner.to_datetime(None) is None

    def test_invalid_returns_default(self, cleaner):
        assert cleaner.to_datetime("not-a-date") is None


# ---------------------------------------------------------------------------
# is_empty
# ---------------------------------------------------------------------------


class TestIsEmpty:
    @pytest.mark.parametrize("value", [None, "", "  ", "n/a", "NA", "null", "None", "-", "--"])
    def test_empty_values(self, cleaner, value):
        assert cleaner.is_empty(value) is True

    @pytest.mark.parametrize("value", [0, False, "0", "hello", [1]])
    def test_non_empty_values(self, cleaner, value):
        assert cleaner.is_empty(value) is False

    def test_empty_list(self, cleaner):
        assert cleaner.is_empty([]) is True

    def test_empty_dict(self, cleaner):
        assert cleaner.is_empty({}) is True

    def test_non_empty_list(self, cleaner):
        assert cleaner.is_empty([1, 2]) is False


# ---------------------------------------------------------------------------
# fill_missing
# ---------------------------------------------------------------------------


class TestFillMissing:
    def test_none_replaced(self, cleaner):
        assert cleaner.fill_missing(None, "default") == "default"

    def test_na_string_replaced(self, cleaner):
        assert cleaner.fill_missing("N/A", "default") == "default"

    def test_non_empty_unchanged(self, cleaner):
        assert cleaner.fill_missing("hello", "default") == "hello"

    def test_zero_unchanged(self, cleaner):
        assert cleaner.fill_missing(0, "default") == 0


# ---------------------------------------------------------------------------
# drop_empty_keys
# ---------------------------------------------------------------------------


class TestDropEmptyKeys:
    def test_removes_none_values(self, cleaner):
        result = cleaner.drop_empty_keys({"a": 1, "b": None, "c": "hello"})
        assert result == {"a": 1, "c": "hello"}

    def test_removes_na_strings(self, cleaner):
        result = cleaner.drop_empty_keys({"a": "N/A", "b": "value"})
        assert result == {"b": "value"}

    def test_keeps_all_when_none_empty(self, cleaner):
        record = {"x": 1, "y": "data"}
        assert cleaner.drop_empty_keys(record) == record


# ---------------------------------------------------------------------------
# deduplicate
# ---------------------------------------------------------------------------


class TestDeduplicate:
    def test_basic_dedup(self, cleaner):
        assert cleaner.deduplicate([1, 2, 1, 3, 2]) == [1, 2, 3]

    def test_preserves_order(self, cleaner):
        assert cleaner.deduplicate([3, 1, 2, 1, 3]) == [3, 1, 2]

    def test_empty_list(self, cleaner):
        assert cleaner.deduplicate([]) == []

    def test_key_function(self, cleaner):
        records = [{"id": 1, "v": "a"}, {"id": 1, "v": "b"}, {"id": 2, "v": "c"}]
        result = cleaner.deduplicate(records, key=lambda r: r["id"])
        assert len(result) == 2
        assert result[0] == {"id": 1, "v": "a"}

    def test_strings(self, cleaner):
        assert cleaner.deduplicate(["a", "b", "a", "c"]) == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# clean_records
# ---------------------------------------------------------------------------


class TestCleanRecords:
    def test_applies_cleaners(self, cleaner):
        records = [{"name": "  Alice ", "age": "30"}]
        result = cleaner.clean_records(
            records, {"name": cleaner.clean_string, "age": cleaner.to_int}
        )
        assert result == [{"name": "Alice", "age": 30}]

    def test_passes_through_unconfigured_fields(self, cleaner):
        records = [{"name": "Alice", "extra": "data"}]
        result = cleaner.clean_records(records, {"name": cleaner.clean_string})
        assert result[0]["extra"] == "data"

    def test_drop_empty_flag(self, cleaner):
        records = [{"name": "Alice", "note": None}]
        result = cleaner.clean_records(records, {}, drop_empty=True)
        assert "note" not in result[0]

    def test_multiple_records(self, cleaner):
        records = [
            {"name": "  Alice ", "score": "10"},
            {"name": "  Bob   ", "score": "20"},
        ]
        result = cleaner.clean_records(
            records, {"name": cleaner.clean_string, "score": cleaner.to_int}
        )
        assert result[0]["name"] == "Alice"
        assert result[1]["score"] == 20

    def test_cleaner_error_falls_back_to_original(self, cleaner):
        def bad_cleaner(v):
            raise ValueError("boom")

        records = [{"x": "original"}]
        result = cleaner.clean_records(records, {"x": bad_cleaner})
        assert result[0]["x"] == "original"
