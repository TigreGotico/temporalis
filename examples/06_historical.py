"""Historical weather via Open-Meteo archive — global, no API key."""
from temporalis.providers.openmeteo_historical import OpenMeteoHistorical

lat, lon = 38.72, -9.14  # Lisbon

# Specific date range
hist = OpenMeteoHistorical(lat, lon, start="2024-07-01", end="2024-07-07")

print("Historical daily summary (2024-07-01 → 2024-07-07):")
for day in hist.days:
    t = day.temperature
    print(f"  {day.datetime.format('YYYY-MM-DD ddd')}  "
          f"{day.summary:<20}  "
          f"min={t.min_val:.1f}°C  max={t.max_val:.1f}°C")

print("\nHourly snapshot (first 6 hours):")
for h in hist.hours[:6]:
    print(f"  {h.datetime.format('HH:mm')}  {h.summary:<20}  {h.temperature}")

# Omit dates to default to yesterday
yesterday = OpenMeteoHistorical(lat, lon)
print(f"\nYesterday summary: {yesterday.weather.summary}, {yesterday.weather.temperature}")
