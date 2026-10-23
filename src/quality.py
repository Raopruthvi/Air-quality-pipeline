"""Data quality checks for one day of readings (the tuples produced by build_rows).

Errors mean "do not load this file". Warnings mean "load it, but tell someone".
"""

from constants import HOURLY_VARIABLES, HOURS_PER_DAY

# Row layout from build_rows(): (city_id, reading_time, pm10, pm2_5, ...)
FIRST_POLLUTANT_INDEX = 2


def column_index(variable):
    return FIRST_POLLUTANT_INDEX + HOURLY_VARIABLES.index(variable)


def check_rows(rows, day):
    """Return (errors, warnings) as lists of messages for one day's rows."""
    errors = []
    warnings = []

    if len(rows) != HOURS_PER_DAY:
        errors.append(f"expected {HOURS_PER_DAY} rows, got {len(rows)}")

    times = [row[1] for row in rows]
    if len(set(times)) != len(times):
        errors.append("duplicate timestamps within the file")
    if any(t.date() != day for t in times):
        errors.append(f"timestamps outside the file's date {day}")

    for variable in HOURLY_VARIABLES:
        index = column_index(variable)
        values = [row[index] for row in rows]
        present = [v for v in values if v is not None]
        missing = len(values) - len(present)

        if rows and not present:
            errors.append(f"{variable} is null for every hour")
        elif missing:
            warnings.append(f"{variable} has {missing} null value(s)")

        if any(v < 0 for v in present):
            errors.append(f"{variable} has negative values")

    pm10_index = column_index("pm10")
    pm25_index = column_index("pm2_5")
    inverted = sum(
        1
        for row in rows
        if row[pm10_index] is not None
        and row[pm25_index] is not None
        and row[pm25_index] > row[pm10_index]
    )
    if inverted:
        warnings.append(f"pm2_5 is higher than pm10 in {inverted} hour(s)")

    return errors, warnings