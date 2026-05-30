# Status: Revive temporalis — core fixes + IPMA + Open-Meteo providers

## Checklist
- [x] Step 1: Fix `as_dict()` mutation bug and replace bare `except:` clauses
- [x] Step 2: Remove dead code (`darksky.py`, `xml.py`) and hardcoded credentials; require explicit OWM key
- [x] Step 3: Clean up geocoding — single Nominatim backend, remove `geocoder` dep and Yandex
- [x] Step 4: Add IPMA provider (`temporalis/providers/ipma.py`)
- [x] Step 5: Add Open-Meteo provider (`temporalis/providers/openmeteo.py`)
- [x] Step 6: Migrate packaging to `pyproject.toml`; remove `setup.py`
- [x] Step 7: Write tests (`test_data_model.py`, `test_owm.py`, `test_ipma.py`, `test_openmeteo.py`)
- [x] Step 8: Update CI workflow — `checkout@v4`, `setup-python@v5`, run pytest, remove license step

## Blockers
<!-- populated by /implement-task if something is stuck -->
