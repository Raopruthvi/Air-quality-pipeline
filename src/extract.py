"""Extract step: fetch hourly air-quality data for several cities over a range
of days, save every raw API response, and print a summary of the combined data.

Usage (run from the project root):
    python src/extract.py                         # 5 days ago (one day)
    python src/extract.py 2026-10-10              # one specific day
    python src/extract.py 2026-10-08 2026-10-12   # every day from start to end
"""

import json
import logging
import sys
import time
from datetime import date, timedelta


import pandas as pd
import requests

from constants import HOURLY_VARIABLES, HOURS_PER_DAY, RAW_DATA_DIR, CITY_COORDINATES
from dates import is_past

logger = logging.getLogger(__name__)

BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

TIMEOUT_SECONDS = 10

DEFAULT_DAYS_BACK = 5
MAX_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 1


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




def split_future_days(days, today):
    """Return (past_days, future_days): days before today, and days that are today or later."""
    past_days = [day for day in days if is_past(day, today)]
    future_days = [day for day in days if not is_past(day, today)]
    return past_days, future_days


def fetch_city_day(lat, lon, day):
    """Call the API for one location and one day (text like '2026-10-12'); return the raw response text.

    Timeouts and connection errors are retried with a doubling wait.
    HTTP errors (4xx/5xx) are not retried and are raised immediately.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "auto",
        "start_date": day,
        "end_date": day,
    }
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(BASE_URL, params=params, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.text
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as err:
            if attempt == MAX_ATTEMPTS:
                raise
            wait = RETRY_WAIT_SECONDS * 2 ** (attempt - 1)
            logger.warning(
                "Attempt %d of %d failed (%s); retrying in %ds",
                attempt, MAX_ATTEMPTS, type(err).__name__, wait,
            )
            time.sleep(wait)


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
            logger.warning("%s has %d rows, expected %d.", city, count, expected_per_city)


def print_summary(frame):
    """Print a human-readable summary (report output, so it uses print, not logging)."""
    print("\nRows per city:")
    print(frame.groupby("city").size())

    print("\nMissing values per column:")
    print(frame[HOURLY_VARIABLES].isna().sum())

    print("\nPM2.5 per city (mean, max):")
    print(frame.groupby("city")["pm2_5"].agg(["mean", "max"]).round(1))


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        start, end = parse_dates(sys.argv[1:])
    except ValueError as err:
        print(f"Invalid dates: {err}")
        print("Usage: python src/extract.py [START_DATE [END_DATE]]   (dates like 2026-10-12)")
        sys.exit(2)

    days = date_range(start, end)
    past_days, future_days = split_future_days(days, date.today())
    if future_days:
        logger.info(
            "Skipping %d future day(s) (%s to %s): forecasts are not used.",
            len(future_days), future_days[0], future_days[-1],
        )
    if not past_days:
        logger.info("Nothing to fetch.")
        return
    expected_rows_per_city = len(past_days) * HOURS_PER_DAY

    frames = []
    failed = []  # list of (city, day) pairs

    for city, (lat, lon) in CITY_COORDINATES.items():
        for day in past_days:
            day_text = day.isoformat()
            try:
                raw_text = fetch_city_day(lat, lon, day_text)
                path = save_raw(city, day_text, raw_text)
                frame = to_dataframe(city, json.loads(raw_text))
            except requests.exceptions.Timeout:
                logger.error("%s %s: request timed out.", city, day_text)
                failed.append((city, day_text))
            except requests.exceptions.HTTPError as err:
                logger.error(
                    "%s %s: HTTP %s - %s",
                    city, day_text, err.response.status_code, err.response.text,
                )
                failed.append((city, day_text))
            except requests.exceptions.RequestException as err:
                logger.error("%s %s: network error (%s).", city, day_text, err)
                failed.append((city, day_text))
            except (KeyError, ValueError) as err:
                logger.error("%s %s: unexpected response format (%r).", city, day_text, err)
                failed.append((city, day_text))
            else:
                if len(frame) != HOURS_PER_DAY:
                    logger.warning(
                        "%s %s returned %d rows, expected %d.",
                        city, day_text, len(frame), HOURS_PER_DAY,
                    )
                logger.info("%s %s: saved %s (%d rows)", city, day_text, path, len(frame))
                frames.append(frame)

    if frames:
        all_data = pd.concat(frames, ignore_index=True)
        report_row_counts(all_data, expected_rows_per_city)
        print_summary(all_data)

    if failed:
        logger.error("FAILED (%d):", len(failed))
        for city, day_text in failed:
            logger.error("  %s %s", city, day_text)
        sys.exit(1)


if __name__ == "__main__":
    main()