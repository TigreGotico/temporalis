"""Basic weather forecast using the registry — no provider class imported directly."""
import temporalis.providers.registry  # noqa: F401 — triggers auto-registration
from temporalis.providers import WeatherProvider

lat, lon = 38.72, -9.14  # Lisbon, Portugal

# Instantiate any registered provider by name
forecast = WeatherProvider.get("openmeteo", lat, lon)

# Current conditions
w = forecast.weather
print(f"Now: {w.summary}")
print(f"  Temperature : {w.temperature}")
print(f"  Feels like  : {w.apparentTemperature}")
print(f"  Humidity    : {w.humidity}")
print(f"  Wind        : {w.windSpeed}")
print(f"  Pressure    : {w.pressure}")
print(f"  Cloud cover : {w.cloudCover}")
print(f"  UV index    : {forecast.uv_index}")

# Sun & moon
print(f"\nSun")
print(f"  Dawn    : {forecast.dawn}")
print(f"  Sunrise : {forecast.sunrise}")
print(f"  Noon    : {forecast.noon}")
print(f"  Sunset  : {forecast.sunset}")
print(f"  Dusk    : {forecast.dusk}")

print(f"\nMoon: {forecast.moon_symbol} {forecast.moon_phase_name} ({forecast.moon_phase:.0%})")

# Daily summary (up to 7 days)
print("\nDaily forecast:")
for day in forecast.days:
    print(f"  {day.datetime.format('ddd DD MMM')}  {day.summary:<20} "
          f"  {day.temperature.min_val:.0f}–{day.temperature.max_val:.0f} °C")

# Hourly summary (first 12 hours)
print("\nHourly (next 12 h):")
for hour in forecast.hours[:12]:
    print(f"  {hour.datetime.format('HH:mm')}  {hour.summary:<20}  {hour.temperature}")
