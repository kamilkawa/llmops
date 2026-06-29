import json
import os
from typing import Annotated

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

GEOCODING_URL = "http://api.openweathermap.org/geo/1.0/direct"
DAILY_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast/daily"
MONTHLY_STATS_URL = "https://history.openweathermap.org/data/2.5/aggregated/month"

mcp = FastMCP("OpenWeatherMap")


def _api_key() -> str:
    key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if not key:
        raise ValueError("OPENWEATHERMAP_API_KEY is not set")
    return key


def _geocode(city: str, country: str = "") -> tuple[float, float, str]:
    query = f"{city},{country}" if country else city
    response = requests.get(
        GEOCODING_URL,
        params={"q": query, "limit": 1, "appid": _api_key()},
        timeout=30,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        raise ValueError(f"Could not find coordinates for '{query}'")
    location = results[0]
    name = location.get("name", city)
    country_code = location.get("country", country)
    label = f"{name}, {country_code}" if country_code else name
    return location["lat"], location["lon"], label


def _kelvin_to_celsius(value: float) -> float:
    return round(value - 273.15, 1)


def _summarize_daily_forecast(data: dict, location_label: str) -> dict:
    days = []
    for entry in data.get("list", []):
        temp = entry.get("temp", {})
        weather = entry.get("weather", [{}])[0]
        days.append(
            {
                "date": entry.get("dt_txt", "")[:10] or entry.get("dt"),
                "description": weather.get("description", ""),
                "temp_min_c": round(temp.get("min", 0), 1),
                "temp_max_c": round(temp.get("max", 0), 1),
                "temp_day_c": round(temp.get("day", 0), 1),
                "humidity_percent": entry.get("humidity"),
                "wind_speed_m_s": entry.get("speed"),
                "precipitation_mm": entry.get("rain", 0) or 0,
                "clouds_percent": entry.get("clouds"),
            }
        )
    return {"location": location_label, "forecast_days": days}


def _summarize_monthly_stats(data: dict, location_label: str, month: int) -> dict:
    result = data.get("result", {})
    temp = result.get("temp", {})
    precipitation = result.get("precipitation", {})
    wind = result.get("wind", {})
    humidity = result.get("humidity", {})
    return {
        "location": location_label,
        "month": month,
        "note": "Statistical averages based on historical data, not a live forecast.",
        "temperature_c": {
            "mean": _kelvin_to_celsius(temp.get("mean", 0)),
            "median": _kelvin_to_celsius(temp.get("median", 0)),
            "average_min": _kelvin_to_celsius(temp.get("average_min", 0)),
            "average_max": _kelvin_to_celsius(temp.get("average_max", 0)),
            "record_min": _kelvin_to_celsius(temp.get("record_min", 0)),
            "record_max": _kelvin_to_celsius(temp.get("record_max", 0)),
        },
        "precipitation_mm": {
            "mean": precipitation.get("mean"),
            "median": precipitation.get("median"),
            "max": precipitation.get("max"),
        },
        "wind_m_s": {
            "mean": wind.get("mean"),
            "max": wind.get("max"),
        },
        "humidity_percent": {
            "mean": humidity.get("mean"),
            "median": humidity.get("median"),
        },
        "sunshine_hours": result.get("sunshine_hours"),
    }


@mcp.tool(
    description=(
        "Get daily weather forecast for up to 16 days. "
        "Returns description, temperature range, humidity, wind, and precipitation."
    )
)
def get_daily_forecast(
    city: Annotated[str, "City name, e.g. Krakow"],
    country: Annotated[str, "ISO 3166-1 alpha-2 country code, e.g. PL"] = "",
    days: Annotated[int, "Number of forecast days between 1 and 16"] = 16,
) -> str:
    lat, lon, location_label = _geocode(city, country)
    days = max(1, min(days, 16))
    response = requests.get(
        DAILY_FORECAST_URL,
        params={
            "lat": lat,
            "lon": lon,
            "cnt": days,
            "units": "metric",
            "appid": _api_key(),
        },
        timeout=30,
    )
    response.raise_for_status()
    return json.dumps(_summarize_daily_forecast(response.json(), location_label), indent=2)


@mcp.tool(
    description=(
        "Get average monthly weather statistics for trip planning beyond 16 days. "
        "Use for long-range planning; returns historical monthly averages."
    )
)
def get_monthly_weather_statistics(
    city: Annotated[str, "City name, e.g. Tokyo"],
    month: Annotated[int, "Month number from 1 (January) to 12 (December)"],
    country: Annotated[str, "ISO 3166-1 alpha-2 country code, e.g. JP"] = "",
) -> str:
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")
    lat, lon, location_label = _geocode(city, country)
    response = requests.get(
        MONTHLY_STATS_URL,
        params={"lat": lat, "lon": lon, "month": month, "appid": _api_key()},
        timeout=30,
    )
    response.raise_for_status()
    return json.dumps(
        _summarize_monthly_stats(response.json(), location_label, month),
        indent=2,
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8010)
