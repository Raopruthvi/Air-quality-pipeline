from datetime import datetime

import pytest

from extract import HOURLY_VARIABLES
from load import build_rows


def make_response(hours=2):
    """A tiny fake API response with `hours` readings, every value 1.0."""
    hourly = {"time": [f"2026-10-05T{h:02d}:00" for h in range(hours)]}
    for var in HOURLY_VARIABLES:
        hourly[var] = [1.0] * hours
    return {"hourly": hourly}


def test_one_tuple_per_hour_with_city_id_and_datetime():
    rows = build_rows(7, make_response(hours=3))
    assert len(rows) == 3
    assert rows[0][0] == 7
    assert rows[0][1] == datetime(2026, 10, 5, 0, 0)


def test_values_follow_hourly_variables_order():
    data = make_response(hours=1)
    for position, var in enumerate(HOURLY_VARIABLES):
        data["hourly"][var] = [position]
    rows = build_rows(1, data)
    assert rows[0][2:] == tuple(range(len(HOURLY_VARIABLES)))


def test_null_becomes_none():
    data = make_response(hours=2)
    data["hourly"]["pm10"][1] = None
    rows = build_rows(1, data)
    pm10_index = 2 + HOURLY_VARIABLES.index("pm10")
    assert rows[1][pm10_index] is None
    assert rows[0][pm10_index] == 1.0


def test_length_mismatch_raises_and_names_the_variable():
    data = make_response(hours=2)
    data["hourly"]["dust"].pop()
    with pytest.raises(ValueError, match="dust"):
        build_rows(1, data)