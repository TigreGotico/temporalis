"""Ensemble provider — merges all free sources for maximum accuracy.

The Ensemble automatically selects every applicable provider for the
coordinates, fetches them in parallel, and merges field-by-field.

Inter-provider disagreement is exposed via DataPoint.min_val / max_val:
a wide spread means the models disagree and the forecast is uncertain.
"""
import temporalis.providers.registry  # noqa: F401
from temporalis.providers.ensemble import Ensemble

lat, lon = 38.7169, -9.1399  # Lisbon — covered by OpenMeteo, MetNo, IPMA

print("Fetching ensemble forecast (parallel)…")
p = Ensemble(lat, lon, units="metric")

print(f"\nProviders loaded: {p.providers}")

w = p.weather
print(f"\n── Current weather ──────────────────────────")
print(f"  Temperature  : {w.temperature}")
if w.temperature.min_val != w.temperature.max_val:
    spread = round(w.temperature.max_val - w.temperature.min_val, 1)
    print(f"  Model spread : ±{spread/2}°C  "
          f"(range {w.temperature.min_val}–{w.temperature.max_val}°C)")
print(f"  Feels like   : {w.apparentTemperature}")
print(f"  Humidity     : {w.humidity}")
print(f"  Dew point    : {w.dewPoint}")
print(f"  Wind         : {w.windSpeed}  bearing {w.windBearing}")
print(f"  Pressure     : {w.pressure}")
print(f"  Cloud cover  : {w.cloudCover}")
print(f"  UV index     : {w.uvIndex}")
if w.waveHeight:
    print(f"  Wave height  : {w.waveHeight}  period {w.wavePeriod}")

print(f"\n── Next 6 hours ─────────────────────────────")
for h in p.hours[:6]:
    spread = ""
    if h.temperature and h.temperature.min_val != h.temperature.max_val:
        spread = f"  [{h.temperature.min_val}–{h.temperature.max_val}]"
    print(f"  {h.datetime.strftime('%H:%M')}  {h.temperature}{spread}  "
          f"precip {h.precipitation or '—'}")

print(f"\n── 3-day outlook ────────────────────────────")
for d in p.days[:3]:
    print(f"  {d.datetime.strftime('%a %d %b')}  "
          f"{d.temperature.min_val}–{d.temperature.max_val}°C  "
          f"{d.summary}")

if p.alerts:
    print(f"\n── Alerts ({len(p.alerts)}) ──────────────────────────")
    for a in p.alerts:
        print(f"  [{a.get('severity', '?')}] {a.get('event')}  {a.get('headline', '')[:60]}")
