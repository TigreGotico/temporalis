"""Derived/approximated weather fields.

temporalis automatically fills in fields that providers don't supply,
using standard meteorological formulas.  This example shows how to
inspect derived values and understand their uncertainty.

Derived fields (filled when provider data is missing):
  dewPoint           — August-Roche-Magnus (error < 0.4°C in valid range)
  apparentTemperature — wind chill (T < 10°C, V > 3 km/h) or
                        heat index (T > 27°C, RH ≥ 40%)
  snow               — precipitation attributed to snow when T ≤ 2°C
  uvIndex            — NOAA solar position + Josefsson cloud attenuation
                        (±1–2 UV index units)
"""
from temporalis.providers.openmeteo import OpenMeteo
from temporalis.derived import (
    approx_dew_point, approx_apparent_temp, approx_snow, approx_uv_index,
)
from temporalis import DataPoint
import pendulum

lat, lon = 38.7169, -9.1399  # Lisbon

print("Fetching OpenMeteo forecast (MetNo natively lacks several fields)…")
p = OpenMeteo(lat, lon, units="metric")
w = p.weather

print(f"\n── Current conditions ───────────────────────")
print(f"  Temperature         : {w.temperature}")
print(f"  Humidity            : {w.humidity}")
print(f"  Wind speed          : {w.windSpeed}")
print(f"  Cloud cover         : {w.cloudCover}")

print(f"\n── Derived fields ───────────────────────────")
print(f"  Dew point           : {w.dewPoint}")
print(f"  Apparent temp       : {w.apparentTemperature}")
print(f"  Snow                : {w.snow or '—  (no precipitation or T > 2°C)'}")
print(f"  UV index            : {w.uvIndex}")

# Show derivation formulas directly
print(f"\n── Manual derivation examples ───────────────")

# Dew point at 20°C, 60% RH
temp = DataPoint("Temperature", 20.0, "°C")
hum  = DataPoint("Humidity", 60.0, "%")
dp   = approx_dew_point(temp, hum)
print(f"  Dew point (20°C, 60% RH)          → {dp}")

# Wind chill at −5°C, 40 km/h
temp_cold = DataPoint("Temperature", -5.0, "°C")
wind      = DataPoint("WindSpeed", 40.0, "km/h")
wc        = approx_apparent_temp(temp_cold, wind_dp=wind)
print(f"  Wind chill (−5°C, 40 km/h)        → {wc}")

# Heat index at 35°C, 75% RH
temp_hot = DataPoint("Temperature", 35.0, "°C")
rh_high  = DataPoint("Humidity", 75.0, "%")
hi       = approx_apparent_temp(temp_hot, humidity_dp=rh_high)
print(f"  Heat index (35°C, 75% RH)         → {hi}")

# Snow at −2°C with 5 mm precipitation
temp_snow  = DataPoint("Temperature", -2.0, "°C")
precip     = DataPoint("Precipitation", 5.0, "mm")
snow       = approx_snow(temp_snow, precip)
print(f"  Snow (−2°C, 5 mm precip)          → {snow}")

# UV index at solar noon on equator, clear sky
dt_noon = pendulum.datetime(2024, 6, 21, 12, 0, 0, tz="UTC")
uv_clear = approx_uv_index(0.0, 0.0, dt_noon)
uv_overcast = approx_uv_index(0.0, 0.0, dt_noon,
                               cloud_cover_dp=DataPoint("CloudCover", 90.0, "%"))
print(f"  UV index (equator noon, clear sky) → {uv_clear}")
print(f"  UV index (equator noon, 90% cloud) → {uv_overcast}")

# Moderate conditions — no formula applies
temp_mod = DataPoint("Temperature", 18.0, "°C")
wind_mod = DataPoint("WindSpeed", 15.0, "km/h")
none_result = approx_apparent_temp(temp_mod, wind_dp=wind_mod)
print(f"\n  Apparent temp (18°C, 15 km/h) → {none_result}  "
      f"(moderate — no formula applicable)")
