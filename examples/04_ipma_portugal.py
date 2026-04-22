"""IPMA — Portugal's national weather service (no API key required)."""
from temporalis.providers.ipma import IPMA

# Works for mainland Portugal, Azores, and Madeira
lat, lon = 38.72, -9.14  # Lisbon

p = IPMA(lat, lon)

w = p.weather
print("Current observation (nearest IPMA station):")
print(f"  Summary     : {w.summary}")
print(f"  Temperature : {w.temperature}")
print(f"  Humidity    : {w.humidity}")
print(f"  Wind speed  : {w.windSpeed}")
print(f"  Pressure    : {w.pressure}")

print("\nIPMA daily forecast (up to 3 days):")
for day in p.days:
    print(f"  {day.datetime.format('ddd DD MMM')}  {day.summary}")

# Sun & moon (computed locally — no network call)
print(f"\nSunrise : {p.sunrise.format('HH:mm')}")
print(f"Sunset  : {p.sunset.format('HH:mm')}")
print(f"Moon    : {p.moon_symbol} {p.moon_phase_name}")

# Weather alerts from IPMA warnings feed
alerts = p.alerts
if alerts:
    print(f"\n{len(alerts)} active alert(s):")
    for a in alerts:
        print(f"  [{a['severity']}] {a['event']} — {a.get('description', '')[:80]}")
else:
    print("\nNo active alerts.")

# Non-Portugal coords raise ValueError
try:
    IPMA(51.5, -0.1)  # London
except ValueError as e:
    print(f"\nExpected error for London: {e}")
