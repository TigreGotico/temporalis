"""Air quality data via Open-Meteo — global, no API key."""
from temporalis.providers.openmeteo_airquality import OpenMeteoAirQuality

lat, lon = 38.72, -9.14  # Lisbon

aq = OpenMeteoAirQuality(lat, lon)

# Current hour snapshot
c = aq.current
print("Current air quality:")
print(f"  EU AQI       : {c.european_aqi}  ({c.summary})")
print(f"  US AQI       : {c.us_aqi}")
print(f"  PM2.5        : {c.pm2_5}")
print(f"  PM10         : {c.pm10}")
print(f"  Ozone        : {c.ozone}")
print(f"  NO₂          : {c.nitrogen_dioxide}")
print(f"  SO₂          : {c.sulphur_dioxide}")
print(f"  CO           : {c.carbon_monoxide}")
print(f"  UV index     : {c.uv_index}")
print(f"  Dust         : {c.dust}")
print(f"  Ammonia      : {c.ammonia}")

# Sun & moon still work — inherited from WeatherProvider
print(f"\nDawn   : {aq.dawn.format('HH:mm')}")
print(f"Dusk   : {aq.dusk.format('HH:mm')}")
print(f"Moon   : {aq.moon_symbol} {aq.moon_phase_name}")

# Hourly breakdown (up to 120 h / 5 days)
print(f"\nHourly AQI forecast ({len(aq.air_quality_hours)} hours):")
for h in aq.air_quality_hours[:6]:
    aqi_val = h.european_aqi.value if h.european_aqi else "—"
    pm25_val = h.pm2_5.value if h.pm2_5 else "—"
    print(f"  {h.datetime.format('ddd HH:mm')}  EU AQI={aqi_val:<5}  PM2.5={pm25_val} µg/m³  ({h.summary})")
