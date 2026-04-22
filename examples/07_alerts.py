"""Weather alerts — IPMA (Portugal) and NWS (USA)."""

# --- IPMA alerts (Portugal) ---
from temporalis.providers.ipma import IPMA

ipma = IPMA(38.72, -9.14)  # Lisbon
alerts = ipma.alerts
if alerts:
    print(f"IPMA — {len(alerts)} active alert(s):")
    for a in alerts:
        print(f"  [{a['severity'].upper()}] {a['event']}")
        if a.get("description"):
            print(f"    {a['description'][:120]}")
        print(f"    Onset: {a.get('onset', '?')}  Expires: {a.get('expires', '?')}")
else:
    print("IPMA — no active alerts for Lisbon.")

print()

# --- NWS alerts (USA) ---
from temporalis.providers.nws import NWS

nws = NWS(40.71, -74.01)  # New York City
alerts = nws.alerts
if alerts:
    print(f"NWS — {len(alerts)} active alert(s):")
    for a in alerts:
        print(f"  [{a['severity'].upper()}] {a['event']}")
        if a.get("headline"):
            print(f"    {a['headline'][:120]}")
        print(f"    Onset: {a.get('onset', '?')}  Expires: {a.get('expires', '?')}")
else:
    print("NWS — no active alerts for New York City.")

# Each alert dict has these keys:
#   event, severity, headline, description, onset, expires
