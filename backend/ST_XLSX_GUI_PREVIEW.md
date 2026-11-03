# ST Excel GUI preview (local pilot)

## Scope

New header button: ST Excel preview. The existing CSV/manual importer is
unchanged and still writes to the legacy catalog; this is not yet suitable
for a hosted personal-upload-only rollout. The ST preview does not save or
import parts, does not call /bulk, and does not make uploaded parts searchable
by the main matching screen. Personal workspace storage is a later change.

POST /api/chips/competitor/st-xlsx-preview accepts multipart file, sheet
(default ProductsList), and optional exact part_number. Each request reparses
the selected file; there is no saved upload identifier or server-side session.
UploadFile temporary storage is closed after each request. This does not make
claims about infrastructure logs, backups, or malicious-upload isolation.

Returns first 20 normalized records, total parsed/matched/error counts,
first 20 rejected-row diagnostics, mappings, unknown fields and provenance.
No fuzzy substitute is selected. Raw source_values are omitted from responses.
The browser clears stale previews when inputs change and cancels stale fetches.
A cancelled browser request does not guarantee the server parser stops early.

## Local validation

Update the feature branch. From backend/:

    .venv-py312\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v

Expected suite count: 49 (37 existing, 7 preview tests, 5 new HTTP tests).
The 7 response-builder tests passed in the assistant environment with a mocked
parser. The 5 HTTP tests are included but were not run there (no FastAPI).
Python syntax checks passed. No frontend build or browser test was run there.

From frontend/, install dependencies with npm ci if package-lock.json exists
(or npm install otherwise), then run npm run build. Restart the backend from
backend/ using:

    .venv-py312\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

Open localhost:8000 and hard-refresh. The frontend must be rebuilt; a cached
frontend/dist will not show the new button. No Node dependency was added.

## Browser acceptance checks

- ST Excel preview opens a separate preview dialog.
- Upload the supplied ST workbook: expect 4930 parsed records and 0 rejected rows.
- Search STM32F051C6T6 exactly: expect 48 MHz, 32 KB Flash, 8 KB RAM,
  LQFP48, -40 to +85 C and 2.0 to 3.6 V from the workbook.
- Search STM32F427ZET6: expect exact-not-found for that workbook.
- Unmapped peripherals show Unknown, not confirmed absent.
- Changing file, sheet or query clears prior results.
- Close preview: no imported-count badge changes and no catalog updates.
- Verify backend/data/competitor_parts.json is unchanged before/after preview.

This change does not address existing CORS/authentication configuration or
provide a complete production file-upload security boundary. Keep the pilot
bound to localhost until the hosted security and personal-storage work is done.
