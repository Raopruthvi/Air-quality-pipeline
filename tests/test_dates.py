from datetime import date

from extract import date_range, split_future_days

TODAY = date(2026, 10, 10)
DAYS = date_range(date(2026, 10, 8), date(2026, 10, 12))


def test_past_days_are_exactly_those_before_today():
    past, future = split_future_days(DAYS, TODAY)
    assert past == [date(2026, 10, 8), date(2026, 10, 9)]


def test_today_counts_as_future():
    past, future = split_future_days(DAYS, TODAY)
    assert TODAY in future
    assert TODAY not in past


def test_split_is_a_clean_partition():
    past, future = split_future_days(DAYS, TODAY)
    assert set(past).isdisjoint(future)
    assert sorted(past + future) == DAYS