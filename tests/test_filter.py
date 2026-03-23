import pytest
from common.filter import (
    FilterEngine,
    FILTER_SEPARATOR_REGEX,
    FILTER_SEPARATOR_EQUALS,
    FILTER_SEPARATOR_NOT_EQUALS,
    FILTER_SEPARATOR_LESS_THAN,
    FILTER_SEPARATOR_GREATER_THAN,
    FILTER_SEPARATOR_LESS_THAN_OR_EQUALS,
    FILTER_SEPARATOR_GREATER_THAN_OR_EQUALS,
    FILTER_SEPARATOR_CONTAINS,
    FILTER_SEPARATOR_NOT_CONTAINS,
    FILTER_SEPARATOR_STARTS_WITH,
    FILTER_SEPARATOR_ENDS_WITH,
)

SAMPLE_DATA = [
    {"name": "Apple", "price": "1.50", "category": "fruit", "code": "A001"},
    {"name": "Banana", "price": "0.75", "category": "fruit", "code": "B002"},
    {"name": "Carrot", "price": "2.00", "category": "vegetable", "code": "C003"},
    {"name": "Date", "price": "5.00", "category": "fruit", "code": "D004"},
    {"name": "Eggplant", "price": "3.25", "category": "vegetable", "code": "E005"},
]

DEFAULT_COLUMNS = ["name", "price", "category"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _engine(data=None, filters=None, columns=None):
    return FilterEngine(
        data=data if data is not None else SAMPLE_DATA,
        filters=filters or [],
        columns=columns or DEFAULT_COLUMNS,
    )


def _names(rows):
    """Return the first column value (name) from each result row."""
    return [row[0] for row in rows]


# ---------------------------------------------------------------------------
# __init__ / _parse_filters
# ---------------------------------------------------------------------------

class TestInit:
    def test_stores_data(self):
        engine = _engine()
        assert engine.data is SAMPLE_DATA

    def test_stores_columns(self):
        engine = _engine(columns=["name", "price"])
        assert engine.columns == ["name", "price"]

    def test_empty_filters_produces_empty_rules(self):
        engine = _engine(filters=[])
        assert engine.filter_rules == {}

    def test_unknown_separator_is_ignored(self):
        engine = _engine(filters=["name~Apple"])
        assert engine.filter_rules == {}

    def test_multiple_filters_parsed(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_EQUALS}Apple", f"category{FILTER_SEPARATOR_EQUALS}fruit"])
        assert len(engine.filter_rules) == 2

    def test_filter_key_is_stripped(self):
        engine = _engine(filters=[f"  name  {FILTER_SEPARATOR_EQUALS}Apple"])
        assert "name" in engine.filter_rules

    def test_filter_value_is_stripped(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_EQUALS}  Apple  "])
        assert engine.filter_rules["name"]["value"] == "Apple"

    def test_regex_filter_compiles_pattern(self):
        import re
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_REGEX}^A"])
        rule = engine.filter_rules["name"]
        assert rule["type"] == FILTER_SEPARATOR_REGEX
        assert hasattr(rule["value"], "search")

    def test_each_separator_type_is_stored(self):
        separators = [
            FILTER_SEPARATOR_EQUALS,
            FILTER_SEPARATOR_NOT_EQUALS,
            FILTER_SEPARATOR_LESS_THAN,
            FILTER_SEPARATOR_GREATER_THAN,
            FILTER_SEPARATOR_LESS_THAN_OR_EQUALS,
            FILTER_SEPARATOR_GREATER_THAN_OR_EQUALS,
            FILTER_SEPARATOR_CONTAINS,
            FILTER_SEPARATOR_NOT_CONTAINS,
            FILTER_SEPARATOR_STARTS_WITH,
            FILTER_SEPARATOR_ENDS_WITH,
        ]
        for sep in separators:
            engine = _engine(filters=[f"name{sep}Apple"])
            assert "name" in engine.filter_rules
            assert engine.filter_rules["name"]["type"] == sep


# ---------------------------------------------------------------------------
# apply_filters — no filters (column projection only)
# ---------------------------------------------------------------------------

class TestApplyFiltersNoFilters:
    def test_returns_all_rows(self):
        result = _engine().apply_filters()
        assert len(result) == len(SAMPLE_DATA)

    def test_rows_are_projected_to_columns(self):
        engine = _engine(columns=["name", "price"])
        result = engine.apply_filters()
        assert result[0] == ["Apple", "1.50"]

    def test_missing_column_defaults_to_empty_string(self):
        engine = _engine(columns=["name", "nonexistent"])
        result = engine.apply_filters()
        assert result[0] == ["Apple", ""]

    def test_single_column(self):
        engine = _engine(columns=["name"])
        result = engine.apply_filters()
        assert result[0] == ["Apple"]

    def test_empty_data_returns_empty_list(self):
        engine = _engine(data=[], filters=[])
        assert engine.apply_filters() == []


# ---------------------------------------------------------------------------
# apply_filters — [re] regex
# ---------------------------------------------------------------------------

class TestRegexFilter:
    def test_matches_regex(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_REGEX}^A"])
        result = _names(engine.apply_filters())
        assert result == ["Apple"]

    def test_no_match_returns_empty(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_REGEX}^Z"])
        assert engine.apply_filters() == []

    def test_partial_regex_match(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_REGEX}rr"])
        result = _names(engine.apply_filters())
        assert result == ["Carrot"]

    def test_case_sensitive_by_default(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_REGEX}apple"])
        assert engine.apply_filters() == []

    def test_multiple_matches(self):
        engine = _engine(filters=[f"category{FILTER_SEPARATOR_REGEX}fruit"])
        result = _names(engine.apply_filters())
        assert set(result) == {"Apple", "Banana", "Date"}


# ---------------------------------------------------------------------------
# apply_filters — [eq] equals
# ---------------------------------------------------------------------------

class TestEqualsFilter:
    def test_exact_match(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_EQUALS}Apple"])
        result = _names(engine.apply_filters())
        assert result == ["Apple"]

    def test_no_match(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_EQUALS}Mango"])
        assert engine.apply_filters() == []

    def test_case_sensitive(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_EQUALS}apple"])
        assert engine.apply_filters() == []

    def test_multiple_matches(self):
        engine = _engine(filters=[f"category{FILTER_SEPARATOR_EQUALS}fruit"])
        result = _names(engine.apply_filters())
        assert set(result) == {"Apple", "Banana", "Date"}


# ---------------------------------------------------------------------------
# apply_filters — [ne] not equals
# ---------------------------------------------------------------------------

class TestNotEqualsFilter:
    def test_excludes_matching_value(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_NOT_EQUALS}Apple"])
        result = _names(engine.apply_filters())
        assert "Apple" not in result

    def test_includes_non_matching_values(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_NOT_EQUALS}Apple"])
        result = _names(engine.apply_filters())
        assert "Banana" in result

    def test_no_match_key_skips_row(self):
        engine = _engine(filters=[f"nonexistent{FILTER_SEPARATOR_NOT_EQUALS}x"])
        assert engine.apply_filters() == []


# ---------------------------------------------------------------------------
# apply_filters — [lt] less than
# ---------------------------------------------------------------------------

class TestLessThanFilter:
    def test_matches_lower_values(self):
        engine = _engine(filters=[f"price{FILTER_SEPARATOR_LESS_THAN}1.00"])
        result = _names(engine.apply_filters())
        assert result == ["Banana"]

    def test_does_not_match_equal_value(self):
        engine = _engine(filters=[f"price{FILTER_SEPARATOR_LESS_THAN}1.50"])
        result = _names(engine.apply_filters())
        assert "Apple" not in result

    def test_no_match(self):
        engine = _engine(filters=[f"price{FILTER_SEPARATOR_LESS_THAN}0.50"])
        assert engine.apply_filters() == []


# ---------------------------------------------------------------------------
# apply_filters — [gt] greater than
# ---------------------------------------------------------------------------

class TestGreaterThanFilter:
    def test_matches_higher_values(self):
        engine = _engine(filters=[f"price{FILTER_SEPARATOR_GREATER_THAN}4.00"])
        result = _names(engine.apply_filters())
        assert result == ["Date"]

    def test_does_not_match_equal_value(self):
        engine = _engine(filters=[f"price{FILTER_SEPARATOR_GREATER_THAN}5.00"])
        assert engine.apply_filters() == []

    def test_no_match(self):
        engine = _engine(filters=[f"price{FILTER_SEPARATOR_GREATER_THAN}10.00"])
        assert engine.apply_filters() == []


# ---------------------------------------------------------------------------
# apply_filters — [lte] less than or equals
# ---------------------------------------------------------------------------

class TestLessThanOrEqualsFilter:
    def test_matches_equal_value(self):
        engine = _engine(filters=[f"price{FILTER_SEPARATOR_LESS_THAN_OR_EQUALS}0.75"])
        result = _names(engine.apply_filters())
        assert result == ["Banana"]

    def test_matches_lower_values(self):
        engine = _engine(filters=[f"price{FILTER_SEPARATOR_LESS_THAN_OR_EQUALS}1.50"])
        result = _names(engine.apply_filters())
        assert set(result) == {"Apple", "Banana"}

    def test_no_match(self):
        engine = _engine(filters=[f"price{FILTER_SEPARATOR_LESS_THAN_OR_EQUALS}0.50"])
        assert engine.apply_filters() == []


# ---------------------------------------------------------------------------
# apply_filters — [gte] greater than or equals
# ---------------------------------------------------------------------------

class TestGreaterThanOrEqualsFilter:
    def test_matches_equal_value(self):
        engine = _engine(filters=[f"price{FILTER_SEPARATOR_GREATER_THAN_OR_EQUALS}5.00"])
        result = _names(engine.apply_filters())
        assert result == ["Date"]

    def test_matches_higher_values(self):
        engine = _engine(filters=[f"price{FILTER_SEPARATOR_GREATER_THAN_OR_EQUALS}3.00"])
        result = _names(engine.apply_filters())
        assert set(result) == {"Date", "Eggplant"}

    def test_no_match(self):
        engine = _engine(filters=[f"price{FILTER_SEPARATOR_GREATER_THAN_OR_EQUALS}10.00"])
        assert engine.apply_filters() == []


# ---------------------------------------------------------------------------
# apply_filters — [contains]
# ---------------------------------------------------------------------------

class TestContainsFilter:
    def test_matches_substring(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_CONTAINS}arr"])
        result = _names(engine.apply_filters())
        assert result == ["Carrot"]

    def test_no_match(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_CONTAINS}xyz"])
        assert engine.apply_filters() == []

    def test_case_sensitive(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_CONTAINS}ARR"])
        assert engine.apply_filters() == []

    def test_full_value_matches(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_CONTAINS}Apple"])
        result = _names(engine.apply_filters())
        assert result == ["Apple"]


# ---------------------------------------------------------------------------
# apply_filters — [not_contains]
# ---------------------------------------------------------------------------

class TestNotContainsFilter:
    def test_excludes_rows_containing_value(self):
        engine = _engine(filters=[f"category{FILTER_SEPARATOR_NOT_CONTAINS}fruit"])
        result = _names(engine.apply_filters())
        assert set(result) == {"Carrot", "Eggplant"}

    def test_includes_all_when_no_match(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_NOT_CONTAINS}xyz"])
        result = engine.apply_filters()
        assert len(result) == len(SAMPLE_DATA)


# ---------------------------------------------------------------------------
# apply_filters — [starts_with]
# ---------------------------------------------------------------------------

class TestStartsWithFilter:
    def test_matches_prefix(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_STARTS_WITH}App"])
        result = _names(engine.apply_filters())
        assert result == ["Apple"]

    def test_no_match(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_STARTS_WITH}pple"])
        assert engine.apply_filters() == []

    def test_case_sensitive(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_STARTS_WITH}app"])
        assert engine.apply_filters() == []

    def test_multiple_matches(self):
        data = [
            {"name": "Avocado", "price": "2.00", "category": "fruit"},
            {"name": "Apple", "price": "1.50", "category": "fruit"},
            {"name": "Banana", "price": "0.75", "category": "fruit"},
        ]
        engine = _engine(data=data, filters=[f"name{FILTER_SEPARATOR_STARTS_WITH}A"])
        result = _names(engine.apply_filters())
        assert set(result) == {"Avocado", "Apple"}


# ---------------------------------------------------------------------------
# apply_filters — [ends_with]
# ---------------------------------------------------------------------------

class TestEndsWithFilter:
    def test_matches_suffix(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_ENDS_WITH}rrot"])
        result = _names(engine.apply_filters())
        assert result == ["Carrot"]

    def test_no_match(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_ENDS_WITH}xyz"])
        assert engine.apply_filters() == []

    def test_case_sensitive(self):
        engine = _engine(filters=[f"name{FILTER_SEPARATOR_ENDS_WITH}RROT"])
        assert engine.apply_filters() == []

    def test_multiple_matches(self):
        data = [
            {"name": "Carrot", "price": "2.00", "category": "vegetable"},
            {"name": "Parrot", "price": "50.00", "category": "bird"},
            {"name": "Apple", "price": "1.50", "category": "fruit"},
        ]
        engine = _engine(data=data, filters=[f"name{FILTER_SEPARATOR_ENDS_WITH}rot"])
        result = _names(engine.apply_filters())
        assert set(result) == {"Carrot", "Parrot"}


# ---------------------------------------------------------------------------
# Rows with missing filter key are excluded
# ---------------------------------------------------------------------------

class TestMissingFilterKey:
    def test_row_without_filter_key_is_excluded(self):
        data = [
            {"name": "Apple", "price": "1.50"},
            {"name": "Banana"},          # missing "price" key
        ]
        engine = _engine(data=data, filters=[f"price{FILTER_SEPARATOR_EQUALS}1.50"])
        result = _names(engine.apply_filters())
        assert result == ["Apple"]

    def test_no_rows_when_key_absent_from_all(self):
        data = [{"name": "Apple"}, {"name": "Banana"}]
        engine = _engine(data=data, filters=[f"price{FILTER_SEPARATOR_EQUALS}1.50"])
        assert engine.apply_filters() == []


# ---------------------------------------------------------------------------
# Column projection via _filter_columns
# ---------------------------------------------------------------------------

class TestFilterColumns:
    def test_projects_specified_columns_in_order(self):
        engine = _engine(columns=["category", "name"])
        row = engine._filter_columns(SAMPLE_DATA[0])
        assert row == ["fruit", "Apple"]

    def test_missing_column_returns_empty_string(self):
        engine = _engine(columns=["name", "missing"])
        row = engine._filter_columns(SAMPLE_DATA[0])
        assert row == ["Apple", ""]
