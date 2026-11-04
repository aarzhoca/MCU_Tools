# Workspace comparison and Excel export (local pilot)

Run matching again after updating. Select 1-3 candidates in Comparison and
Excel export, including FAIL/UNKNOWN records if useful for gap analysis.
Only the returned records (up to five per result group) are selectable.
FAIL/UNKNOWN comparisons are not recommendations. No ranking changes occur.

One frozen snapshot supplies both the browser table and Excel. The workbook
has Summary, Comparison, and Sources sheets. Requirements, source values,
candidate values, per-field check/quality labels, overall eligibility,
evidence references, UTC generation time, application/comparison/ranking
versions and a SHA-256 of the loaded catalog are included. The signature is
not datasheet verification or engineering approval. Unreferenced fields
remain catalog/unknown, not independently verified. Missing values stay
Unknown; unchecked parameters are NOT_CHECKED, never automatically PASS.

## Integrity and lifecycle

The match endpoint adds comparison_snapshot_json and snapshot_token. The
original JSON string is kept unchanged through the browser, avoiding numeric
reserialization differences (48.0 versus 48). POST /api/workspace/export-xlsx
accepts that string, token and selected part numbers. It verifies HMAC,
age and selection, then renders without reading the catalog or reranking.
Snapshots expire after eight hours. The key is random and process-local:
restart/reload invalidates it; use one Uvicorn worker for this local pilot.
A multi-worker/hosted rollout needs shared-key lifecycle and access controls.
No workspace, uploaded file or export is persistently stored by this code.
Normal infrastructure buffers/logs remain outside that claim.

Workbook strings are explicitly literal text, not Excel formulas. Text that
cannot fit an Excel cell is rejected rather than silently truncated.
Snapshot size is bounded at 400,000 bytes; export request at 1,000,000 bytes.
These limits do not constitute full production upload/security hardening.
The existing CSV/manual import routes still write to the master catalog.

## Validation

14 synthetic snapshot/XLSX-readback tests passed in the assistant environment
with openpyxl. They cover frozen values, UNKNOWN, selection limits, signatures,
expiry, evidence, numeric cells, formula-like literal text and 3 candidates.
Four new HTTP tests use real matching/export code with synthetic catalog I/O,
but were NOT run there because FastAPI is unavailable. No frontend build,
browser download or complete-suite pass is claimed there.

Expected total: 94 tests (76 previous + 14 export + 4 HTTP). From backend/:

    .venv-py312\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v

Rebuild frontend with npm run build. Restart the same updated backend on the
chosen localhost port, hard-refresh, then run matching again to get a new
snapshot. Select M031LC2AE and an UNKNOWN candidate; compare the temperature
row on screen and in Excel. Check the sourced -40 C reference on Sources,
unknown stays Unknown, and the disclaimer is on Summary. Change requirements:
previous results/comparison must disappear. Clearing/closing discards state.
A restart requires matching again before exporting. No dependency changes.
