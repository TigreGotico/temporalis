"""Provider registry — list, select, and swap providers at runtime."""
import temporalis.providers.registry  # noqa: F401
from temporalis.providers import WeatherProvider

lat, lon = 38.72, -9.14  # Lisbon

# List every built-in provider
print("Available providers:", WeatherProvider.available())

# Get the same location from multiple keyless providers and compare
results = WeatherProvider.compare(["openmeteo", "metno"], lat, lon)

print("\nSide-by-side comparison:")
print(f"{'Provider':<20} {'Summary':<25} {'Temp':<12} {'Humidity'}")
print("-" * 70)
for name, d in results.items():
    if "error" in d:
        print(f"{name:<20} ERROR: {d['error']}")
    else:
        temp = str(d["temperature"])
        hum  = str(d["humidity"])
        print(f"{name:<20} {str(d['summary']):<25} {temp:<12} {hum}")

# Instantiate by name — useful when the provider is a config value
provider_name = "openmeteo"
p = WeatherProvider.get(provider_name, lat, lon)
print(f"\n{p}")  # uses __repr__: ProviderClass(lat, lon) — summary temp
