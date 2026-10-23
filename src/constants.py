from pathlib import Path
HOURLY_VARIABLES = ["pm10", "pm2_5", "carbon_monoxide", "dust", "carbon_dioxide", "nitrogen_dioxide"]
CITY_COORDINATES = {
    "Mangaluru": (12.9156, 74.8560),
    "Bengaluru": (12.9716, 77.5946),
    "Delhi": (28.6139, 77.2090),
    "Chennai": (13.0827, 80.2707),
}
RAW_DATA_DIR = Path("data/raw")
HOURS_PER_DAY = 24