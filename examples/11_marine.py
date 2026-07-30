"""Marine weather — wave, swell, wind-wave, and ocean current forecast.

OpenMeteoMarine is free and requires no API key. It only works for
coordinates over open ocean — landlocked points raise ValueError.
"""
from temporalis.providers.openmeteo_marine import OpenMeteoMarine

# Atlantic coast near Lisbon
lat, lon = 38.7169, -9.5

print("Fetching marine forecast…")
p = OpenMeteoMarine(lat, lon, units="metric", forecast_days=3)

w = p.weather
print(f"\n── Current marine conditions ────────────────")
print(f"  Significant wave height : {w.waveHeight}")
print(f"  Wave period             : {w.wavePeriod}")
print(f"  Wave direction          : {w.waveDirection}")
print(f"  Swell height            : {w.swellHeight}")
print(f"  Swell period            : {w.swellPeriod}")
print(f"  Swell direction         : {w.swellDirection}")
print(f"  Wind-wave height        : {w.windWaveHeight}")
print(f"  Ocean current           : {w.currentVelocity}  dir {w.currentDirection}")

print(f"\n── Hourly wave forecast (next 12 h) ─────────")
print(f"  {'Time':<8}  {'Wave H':>8}  {'Period':>8}  {'Swell H':>8}")
for h in p.hours[:12]:
    wh  = f"{h.waveHeight.value:.1f} m"  if h.waveHeight  else "—"
    wp  = f"{h.wavePeriod.value:.0f} s"  if h.wavePeriod  else "—"
    swh = f"{h.swellHeight.value:.1f} m" if h.swellHeight else "—"
    print(f"  {h.datetime.strftime('%H:%M'):<8}  {wh:>8}  {wp:>8}  {swh:>8}")

print(f"\n── Daily wave outlook ───────────────────────")
for d in p.days:
    wh = f"{d.waveHeight.value:.1f} m" if d.waveHeight else "—"
    print(f"  {d.datetime.strftime('%a %d %b')}  max wave {wh}")

# US units example
print(f"\n── Same data in imperial units ──────────────")
p_us = OpenMeteoMarine(lat, lon, units="us")
wu = p_us.weather
print(f"  Wave height : {wu.waveHeight}")
print(f"  Current     : {wu.currentVelocity}")
