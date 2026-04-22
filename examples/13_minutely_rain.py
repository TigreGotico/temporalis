"""Minutely precipitation — per-minute rain intensity for the next hour.

Only OWM One Call 3.0 supports minutely data (requires a paid key).
The provider falls back gracefully when the key lacks One Call access.

This example also shows how to check for rain in the next N minutes,
which is useful for "will it rain in the next 30 minutes?" queries.
"""
import os
from temporalis.providers.owm import OWM

key = os.environ.get("OWM_KEY")  # set to a One Call 3.0 key to get real data
lat, lon = 38.7169, -9.1399

print("Fetching OWM forecast with minutely data…")
p = OWM(lat, lon, units="metric", key=key)

mf = p.minutely
if not mf or len(mf) == 0:
    print("\nNo minutely data available.")
    print("  → OWM One Call 3.0 subscription required, or no radar coverage here.")
else:
    print(f"\n── Next {len(mf)} minutes of precipitation ──────────")
    max_precip = max((m.precipitation.value for m in mf
                      if m.precipitation and m.precipitation.value), default=0)
    if max_precip == 0:
        print("  No rain expected in the next hour.")
    else:
        for m in mf:
            val = m.precipitation.value if m.precipitation else 0.0
            bar = "█" * int(val * 4)
            print(f"  {m.datetime.strftime('%H:%M')}  {val:5.2f} mm/h  {bar}")

    # "Will it rain in the next 30 minutes?"
    rain_soon = any(
        m.precipitation and m.precipitation.value and m.precipitation.value > 0.1
        for m in list(mf)[:30]
    )
    print(f"\n  Rain in the next 30 min: {'YES' if rain_soon else 'no'}")

print(f"\n── Current weather ──────────────────────────")
w = p.weather
print(f"  {w.temperature}  {w.summary}")
print(f"  Precipitation: {w.precipitation or '—'}")
