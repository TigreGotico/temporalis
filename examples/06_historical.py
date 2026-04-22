"""Historical weather via Open-Meteo archive — global, no API key.

Pass start= (and optionally end=) to OpenMeteo to use the archive API.
Omit them for the default forecast mode.
"""
from temporalis.providers.openmeteo import OpenMeteo

lat, lon = 38.72, -9.14  # Lisbon

# Specific date range — hits archive-api.open-meteo.com
hist = OpenMeteo(lat, lon, start="2024-07-01", end="2024-07-07")
print(f"Historical mode: {hist.historical}")

print("Historical daily summary (2024-07-01 → 2024-07-07):")
for day in hist.days:
    t = day.temperature
    print(f"  {day.datetime.format('YYYY-MM-DD ddd')}  "
          f"{day.summary:<20}  "
          f"min={t.min_val:.1f}°C  max={t.max_val:.1f}°C")

print("\nHourly snapshot (first 6 hours):")
for h in hist.hours[:6]:
    print(f"  {h.datetime.format('HH:mm')}  {h.summary:<20}  {h.temperature}")

# Single day
single = OpenMeteo(lat, lon, start="2024-07-04")
print(f"\nSingle day: {single.days[0].datetime.format('YYYY-MM-DD')}")

# Normal forecast (no dates)
forecast = OpenMeteo(lat, lon)
print(f"\nForecast mode: {forecast.historical}")
print(f"Today: {forecast.weather.summary}, {forecast.weather.temperature}")
