"""Extract step: fetch hourly air-quality data for several cities over a range
of days, save every raw API response, and print a summary of the combined data.

Usage (run from the project root):
    python src/extract.py                         # 5 days ago (one day)
    python src/extract.py 2026-10-10              # one specific day
    python src/extract.py 2026-10-08 2026-10-12   # every day from start to end
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
HOURLY_VARIABLES = ["pm10", "pm2_5", "carbon_monoxide", "dust", "carbon_dioxide", "nitrogen_dioxide"]
CITY_COORDINATES = {
    "Mangaluru": (12.9156, 74.8560),
    "Bengaluru": (12.9716, 77.5946),
    "Delhi": (28.6139, 77.2090),
    "Chennai": (13.0827, 80.2707),
}
RAW_DATA_DIR = Path("data/raw")
TIMEOUT_SECONDS = 10
HOURS_PER_DAY = 24
DEFAULT_DAYS_BACK = 5


def parse_dates(args):
    """Turn the command-line arguments into a (start, end) pair of dates."""
    if len(args) == 2:
        start, end = date.fromisoformat(args[0]), date.fromisoformat(args[1])
    elif len(args) == 1:
        start = end = date.fromisoformat(args[0])
    else:
        start = end = date.today() - timedelta(days=DEFAULT_DAYS_BACK)

    if end < start:
        raise ValueError("end date is before start date")
    return start, end


def date_range(start, end):
    """Return every date from start to end, including both."""
    days = []
    current = start
    while current <= end:
        days.append(current)
        current = current + timedelta(days=1)
    return days


def fetch_city_day(lat, lon, day):
    """Call the API for one location and one day (text like '2026-10-12'); return the raw response text."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "auto",
        "start_date": day,
        "end_date": day,
    }
    response = requests.get(BASE_URL, params=params, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text


def save_raw(city, day, raw_text):
    """Save the response exactly as received: data/raw/<city>/<day>.json."""
    folder = RAW_DATA_DIR / city.lower()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{day}.json"
    path.write_text(raw_text, encoding="utf-8")
    return path


def to_dataframe(city, data):
    """Turn the 'hourly' section of the response into a table with a city column."""
    frame = pd.DataFrame(data["hourly"])
    frame["time"] = pd.to_datetime(frame["time"])
    frame.insert(0, "city", city)
    return frame


def report_row_counts(frame, expected_per_city):
    """Warn about any city whose total row count is not what we expect."""
    for city, count in frame.groupby("city").size().items():
        if count != expected_per_city:
            print(f"Warning: {city} has {count} rows, expected {expected_per_city}.")


def print_summary(frame):
    print("\nRows per city:")
    print(frame.groupby("city").size())

    print("\nMissing values per column:")
    print(frame[HOURLY_VARIABLES].isna().sum())

    print("\nPM2.5 per city (mean, max):")
    print(frame.groupby("city")["pm2_5"].agg(["mean", "max"]).round(1))


def main():
    try:
        start, end = parse_dates(sys.argv[1:])
    except ValueError as err:
        print(f"Invalid dates: {err}")
        print("Usage: python src/extract.py [START_DATE [END_DATE]]   (dates like 2026-10-12)")
        sys.exit(2)

    days = date_range(start, end)
    expected_rows_per_city = HOURS_PER_DAY * len(days)

    frames = []
    failed = []  # list of (city, day) pairs

    for city, (lat, lon) in CITY_COORDINATES.items():
        for day in days:
            day_text = day.isoformat()
            try:
                raw_text = fetch_city_day(lat, lon, day_text)
                path = save_raw(city, day_text, raw_text)
                frame = to_dataframe(city, json.loads(raw_text))
            except requests.exceptions.Timeout:
                print(f"{city} {day_text}: request timed out.")
                failed.append((city, day_text))
            except requests.exceptions.HTTPError as err:
                print(f"{city} {day_text}: HTTP {err.response.status_code} - {err.response.text}")
                failed.append((city, day_text))
            except requests.exceptions.RequestException as err:
                print(f"{city} {day_text}: network error ({err}).")
                failed.append((city, day_text))
            except (KeyError, ValueError) as err:
                print(f"{city} {day_text}: unexpected response format ({err!r}).")
                failed.append((city, day_text))
            else:
                if len(frame) != HOURS_PER_DAY:
                    print(f"Warning: {city} {day_text} returned {len(frame)} rows, expected {HOURS_PER_DAY}.")
                print(f"{city} {day_text}: saved {path} ({len(frame)} rows)")
                frames.append(frame)

    if frames:
        all_data = pd.concat(frames, ignore_index=True)
        report_row_counts(all_data, expected_rows_per_city)
        print_summary(all_data)

    if failed:
        print(f"\nFAILED ({len(failed)}):")
        for city, day_text in failed:
            print(f"  {city} {day_text}")
        sys.exit(1)


if __name__ == "__main__":
    main()