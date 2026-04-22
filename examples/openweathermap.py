"""OpenWeatherMap provider — requires an API key (a working default is bundled)."""
from temporalis.providers.owm import OWM

lat, lon = 38.72, -9.14  # Lisbon

# Uses bundled default key; pass key="YOUR_KEY" to use your own
p = OWM(lat, lon)
# or: p = OWM.from_address("Lisbon, Portugal")

print("##### CURRENT WEATHER ######")
p.print()

print("\n##### DAILY FORECAST ######")
p.print_daily()

print("\n##### HOURLY FORECAST ######")
p.print_hourly()

print("\n##### SUN & MOON ######")
print("Dawn   :", p.dawn)
print("Sunrise:", p.sunrise)
print("Sunset :", p.sunset)
print("Dusk   :", p.dusk)
print("Moon   :", p.moon_symbol, p.moon_phase_name)

# Tomorrow
tomorrow = p.weather_tomorrow
print("\nTomorrow:", tomorrow.summary, tomorrow.temperature)
