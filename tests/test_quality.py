from datetime import date, datetime

from extract import HOURLY_VARIABLES
from quality import check_rows, column_index

DAY = date(2026, 10, 5)


def make_rows(day=DAY, hours=24, value=10.0):
    """A clean fake day: one tuple per hour, every pollutant equal to `value`."""
    return [
        (1, datetime(day.year, day.month, day.day, hour)) + (value,) * len(HOURLY_VARIABLES)
        for hour in range(hours)
    ]


def with_value(rows, hour, variable, value):
    """Return a copy of rows with one pollutant value changed at one hour."""
    rows = list(rows)
    row = list(rows[hour])
    row[column_index(variable)] = value
    rows[hour] = tuple(row)
    return rows


def test_clean_day_has_no_problems():
    errors, warnings = check_rows(make_rows(), DAY)
    assert errors == []
    assert warnings == []


def test_wrong_row_count_is_an_error():
    errors, warnings = check_rows(make_rows(hours=23), DAY)
    assert any("expected 24 rows, got 23" in message for message in errors)


def test_negative_value_is_an_error():
    rows = with_value(make_rows(), hour=3, variable="pm10", value=-1.0)
    errors, warnings = check_rows(rows, DAY)
    assert any("pm10 has negative values" in message for message in errors)


def test_duplicate_timestamps_are_an_error():
    rows = make_rows()
    rows[5] = rows[4]
    errors, warnings = check_rows(rows, DAY)
    assert any("duplicate timestamps" in message for message in errors)


def test_timestamps_from_another_date_are_an_error():
    rows = make_rows(day=date(2026, 10, 6))
    errors, warnings = check_rows(rows, DAY)
    assert any("outside the file's date" in message for message in errors)


def test_single_null_is_only_a_warning():
    rows = with_value(make_rows(), hour=0, variable="pm10", value=None)
    errors, warnings = check_rows(rows, DAY)
    assert errors == []
    assert any("pm10 has 1 null value(s)" in message for message in warnings)


def test_column_null_for_every_hour_is_an_error():
    rows = make_rows()
    for hour in range(24):
        rows = with_value(rows, hour=hour, variable="carbon_dioxide", value=None)
    errors, warnings = check_rows(rows, DAY)
    assert any("carbon_dioxide is null for every hour" in message for message in errors)


def test_pm25_higher_than_pm10_is_only_a_warning():
    rows = with_value(make_rows(), hour=2, variable="pm2_5", value=50.0)
    errors, warnings = check_rows(rows, DAY)
    assert errors == []
    assert any("pm2_5 is higher than pm10 in 1 hour(s)" in message for message in warnings)