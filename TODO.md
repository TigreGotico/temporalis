# TODO — temporalis

## Open issues

None open.

## Gaps

- [ ] `pyproject.toml` `Homepage` points at `OpenJarbas/temporalis`; should be `JarbasAl/temporalis`.
- [ ] Remove legacy inline workflow `build_tests.yml` (duplicates gh-automations `build-tests.yml`).
- [ ] Remove legacy inline workflow `license_tests.yml`; it duplicates gh-automations `license_check.yml` and installs a Neon-org lichecker fork (`git+https://github.com/NeonJarbas/lichecker`) — disallowed Neon reference.
- [ ] No `dev` branch on the remote, yet most workflows trigger on `dev` (build-tests, coverage, license-check, release-preview, pip_audit, release_workflow). Create `dev` or the PR-gated CI never runs.
- [ ] Dependency drift: `requirements.txt` lists `geocoder`, `python-dateutil`, `pytz`, `requests-cache` not in `pyproject.toml`; reconcile or drop `requirements.txt`.
- [ ] Local scratch artifacts present on disk (`temporalis.egg-info/`, `.pytest_cache/`, `__pycache__/`) — gitignored and not tracked, safe to delete from the working tree.
- [ ] Repo retains planning scaffolding at root (`brainstorm.md`, `spec.md`, `plan.md`, `sprint.md`, `status.md`, `decisions.md`, `implementation-notes.md`, `WORKSPACE_AUDIT.md`); decide whether these belong in the published repo or `docs/`.

## Code TODOs

None found.
