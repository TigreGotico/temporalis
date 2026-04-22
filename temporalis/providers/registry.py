"""Auto-register all built-in providers into WeatherProvider._registry."""
from temporalis.providers import WeatherProvider
from temporalis.providers.owm import OWM
from temporalis.providers.ipma import IPMA
from temporalis.providers.openmeteo import OpenMeteo
from temporalis.providers.metno import MetNo
from temporalis.providers.nws import NWS
from temporalis.providers.openmeteo_historical import OpenMeteoHistorical

WeatherProvider.register("owm", OWM)
WeatherProvider.register("ipma", IPMA)
WeatherProvider.register("openmeteo", OpenMeteo)
WeatherProvider.register("metno", MetNo)
WeatherProvider.register("nws", NWS)
WeatherProvider.register("openmeteo_historical", OpenMeteoHistorical)
