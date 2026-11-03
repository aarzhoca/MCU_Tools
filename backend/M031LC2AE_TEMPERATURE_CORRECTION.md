# Sourced M031LC2AE minimum operating temperature

## Evidence and scope

Nuvoton's exact M031LC2AE product page states, under Key Features / Operating
Characteristics: "Temperature range: - 40°C to +105°C".

https://www.nuvoton.com/products/microcontrollers/arm-cortex-m0-mcus/m031-series/m031lc2ae/

Checked 2026-11-03. This correction concerns operating temperature, not
storage or junction temperature. Only M031LC2AE / temp_min_c is corrected.
Other devices and all other specification values are unchanged.

## Implementation

backend/data/nuvoton_corrections.json holds the explicit value and evidence.
get_nuvoton_parts() applies it to a copy of the raw catalog at load time.
No rewrite of nuvoton_parts.json is needed. Existing imports can regenerate
that raw file without losing the correction as long as they retain this
correction file and the application continues using the updated loader.
Direct consumers of the raw JSON, bypassing the loader, do not see the fix.
The correction file must be included in deployment/data-volume updates.

Missing/null minimum temperature becomes -40 with field_quality=verified
for that field only and a field_sources entry. Other fields retain their
existing evidence status. A conflicting non-null value is NOT overwritten:
it is preserved, marked unverified and recorded in catalog_correction_conflicts.
No rule treats an arbitrary unknown value as a pass. This is not a family
or catalog-wide default. Raw source catalog values are not mutated in memory.

Legacy ChipSpec list responses still omit new evidence fields; workspace
checks consume the corrected raw catalog. The evidence file remains the
traceable source until richer comparison/export schemas expose it.

## Validation

9 synthetic/temporary-file tests passed in the assistant environment,
including eight-check PASS, missing-value UNKNOWN, conflict handling,
non-target isolation and reloading after simulated catalog regeneration.
A further direct check confirmed conflict-overlay idempotency. Two real
local-catalog tests are included but were NOT run there because the complete
repository catalog was not available in that execution environment.
No complete-suite or live matching pass is claimed.

Expected suite: 76 tests (65 previous + 9 correction tests + 2 real-catalog
checks). From backend/:

    .venv-py312\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v

Restart the backend (or clear loader caches) after updating. No frontend
change or npm rebuild is required for this correction. Reopen the workspace,
set all eight original requirements, then match again. M031LC2AE should pass
the minimum-temperature check; overall PASS still depends on every check.
M032LC2AE and other uncorrected records may remain UNKNOWN. Never fill them
by inference from this single-part correction.
