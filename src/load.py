"""Load step: read saved raw API responses, check their quality, and upsert them into PostgreSQL.

Usage (run from the project root, with the database container running):
    python src/load.py
"""

import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

import psycopg

from config import get_db_url
from constants import CITY_COORDINATES, HOURLY_VARIABLES, RAW_DATA_DIR
from dates import is_past
from quality import check_rows

logger = logging.getLogger(__name__)

UPSERT_CITY_SQL = """
INSERT INTO dim_city (city_name, latitude, longitude)
VALUES (%s, %s, %s)
ON CONFLICT (city_name) DO UPDATE
SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude
"""

# The column order here must match the tuple order produced by build_rows().
UPSERT_READING_SQL = """
INSERT INTO fact_air_quality
    (city_id, reading_time, pm10, pm2_5, carbon_monoxide, dust, carbon_dioxide, nitrogen_dioxide)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (city_id, reading_time) DO UPDATE SET
    pm10 = EXCLUDED.pm10,
    pm2_5 = EXCLUDED.pm2_5,
    carbon_monoxide = EXCLUDED.carbon_monoxide,
    dust = EXCLUDED.dust,
    carbon_dioxide = EXCLUDED.carbon_dioxide,
    nitrogen_dioxide = EXCLUDED.nitrogen_dioxide
"""


def upsert_cities(conn):
    with conn.cursor() as cur:
        for city, (lat, lon) in CITY_COORDINATES.items():
            cur.execute(UPSERT_CITY_SQL, (city, lat, lon))


def get_city_ids(conn):
    """Return a dict mapping city name to city_id, e.g. {"Mangaluru": 1}."""
    with conn.cursor() as cur:
        cur.execute("SELECT city_name, city_id FROM dim_city")
        rows = cur.fetchall()
    return {city_name: city_id for city_name, city_id in rows}


def read_raw_file(path):
    """Read one saved API response and return it as a Python dictionary."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_rows(city_id, data):
    """Turn one day's response into a list of (city_id, time, pm10, ...) tuples."""
    hourly = data["hourly"]
    expected = len(hourly["time"])
    for var in HOURLY_VARIABLES:
        if len(hourly[var]) != expected:
            raise ValueError(f"{var} has {len(hourly[var])} values, expected {expected}.")

    rows = []
    for i, reading_time in enumerate(hourly["time"]):
        row = [city_id, datetime.fromisoformat(reading_time)]
        for var in HOURLY_VARIABLES:
            row.append(hourly[var][i])  # JSON null becomes None, stored as NULL
        rows.append(tuple(row))
    return rows


def upsert_readings(conn, rows):
    with conn.cursor() as cur:
        cur.executemany(UPSERT_READING_SQL, rows)


def load_all_files(conn, city_ids):
    """Load every saved past-day file under data/raw/<city>/<date>.json."""
    ids_by_folder = {name.lower(): city_id for name, city_id in city_ids.items()}
    loaded_rows = 0
    skipped = []
    failed = []
    today = date.today()

    for path in sorted(RAW_DATA_DIR.glob("*/*.json")):
        try:
            day = date.fromisoformat(path.stem)
            if not is_past(day, today):
                skipped.append(path)  # forecast data is not loaded
                continue
            data = read_raw_file(path)
            rows = build_rows(ids_by_folder[path.parent.name], data)
        except (KeyError, ValueError) as err:
            logger.error("%s: could not be read (%r)", path, err)
            failed.append(path)
            continue

        errors, warnings = check_rows(rows, day)
        for message in warnings:
            logger.warning("%s: %s", path, message)
        if errors:
            for message in errors:
                logger.error("%s: %s", path, message)
            failed.append(path)
            continue

        upsert_readings(conn, rows)
        loaded_rows += len(rows)
        logger.info("%s: %d rows", path, len(rows))

    return loaded_rows, skipped, failed


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    with psycopg.connect(get_db_url()) as conn:
        upsert_cities(conn)
        city_ids = get_city_ids(conn)
        loaded_rows, skipped, failed = load_all_files(conn, city_ids)
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM fact_air_quality")
            total = cur.fetchone()[0]

    logger.info("Processed %d rows. Table now holds %d rows.", loaded_rows, total)
    if skipped:
        logger.info("Skipped %d file(s) dated today or later (forecasts).", len(skipped))
    if failed:
        logger.error("FAILED to load %d file(s).", len(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()