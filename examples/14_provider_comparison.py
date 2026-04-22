"""Compare multiple providers side-by-side for the same location.

Useful for validating the Ensemble merge or understanding how providers
diverge.  Fetched in parallel via ThreadPoolExecutor.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from temporalis.providers.openmeteo import OpenMeteo
from temporalis.providers.metno import MetNo

lat, lon = 38.7169, -9.1399  # Lisbon

PROVIDERS = [
    ("OpenMeteo", lambda: OpenMeteo(lat, lon, units="metric")),
    ("MetNo",     lambda: MetNo(lat, lon, units="metric")),
]

print(f"Fetching {len(PROVIDERS)} providers in parallel…\n")

results = {}
with ThreadPoolExecutor() as pool:
    futures = {pool.submit(fn): name for name, fn in PROVIDERS}
    for f in as_completed(futures):
        name = futures[f]
        try:
            results[name] = f.result()
        except Exception as exc:
            print(f"  {name} failed: {exc}")

# Current weather table
fields = [
    ("temperature",       "Temperature"),
    ("apparentTemperature","Feels like"),
    ("humidity",          "Humidity"),
    ("dewPoint",          "Dew point"),
    ("windSpeed",         "Wind speed"),
    ("windBearing",       "Wind dir"),
    ("pressure",          "Pressure"),
    ("cloudCover",        "Cloud cover"),
    ("uvIndex",           "UV index"),
    ("precipitation",     "Precipitation"),
]

header = f"{'Field':<18}" + "".join(f"{n:>16}" for n in results)
print(header)
print("─" * len(header))

for attr, label in fields:
    row = f"{label:<18}"
    for name, p in results.items():
        w = p.weather
        dp = getattr(w, attr, None)
        cell = str(dp) if dp and dp.value is not None else "—"
        row += f"{cell:>16}"
    print(row)

# Hourly temperature comparison
print(f"\n── Hourly temperature (next 6 h) ────────────")
header2 = f"{'Time':<8}" + "".join(f"{n:>14}" for n in results)
print(header2)

# Collect hours by rounded timestamp
from collections import defaultdict
import pendulum

buckets = defaultdict(dict)
for name, p in results.items():
    for h in p.hours[:12]:
        key = h.datetime.start_of("hour").isoformat()
        buckets[key][name] = h

for key in sorted(buckets)[:6]:
    slot = buckets[key]
    dt = pendulum.parse(key)
    row = f"{dt.strftime('%H:%M'):<8}"
    for name in results:
        h = slot.get(name)
        if h and h.temperature:
            row += f"{str(h.temperature):>14}"
        else:
            row += f"{'—':>14}"
    print(row)
