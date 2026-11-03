# Temporary ST workspace matching (local pilot)

## Workflow

ST Excel preview -> exact source row -> Use this part -> edit customer
requirements -> Find Nuvoton candidates. The results stay inside the dialog;
the main catalog search and /api/match are unchanged.

The selected source and match results live in React component memory, not
localStorage, cookies, a database or the master catalog. Clear workspace drops
the active selection/results and returns to the retained workbook preview.
Closing the dialog or refreshing discards the file, preview and selection.
The backend endpoint is stateless; normal HTTP/framework infrastructure can
still create temporary buffers and logs. This is not authenticated hosted
multi-user storage or a production security boundary.

## API

POST /api/workspace/match accepts source (raw preview record), optional
requirements, characteristics and top_k (1..20). Requirements reuse the
validated rules from the existing mandatory-check API. No source-part fuzzy
lookup occurs. Browser-supplied source/provenance is not cryptographically
verified or independently checked against a datasheet.

The existing matcher always scores CPU frequency, GPIO, package area, Flash
and RAM. This adapter requires all those source values to be present and
non-estimated. Package area must be explicit and positive: no fallback area
is used to establish availability. Missing source base fields produce 422,
not zero-filled values. Optional unknown source ranking fields are omitted
and named in the response. Candidate missing ranking data or invalid legacy
schema is unranked with a reason; FAIL/UNKNOWN mandatory checks cannot enter
the ranked list. Requirement totals are counted before per-group limits.
No requirements means NOT_EVALUATED, not PASS.

Requirements are separate from source values. Initial UI thresholds come
from the source but are editable; only frequency/Flash/RAM start checked.
For the agreed first example, explicitly set voltage/temperature/package
requirements as desired. The source T6 record stays +85 C and 2.0 V minimum,
even if the customer requests +105 C and 1.8 V. A candidate with missing
minimum-temperature data remains UNKNOWN when that requirement is checked.
PASS means only the checked requirements; it does not establish pin or
firmware compatibility, simultaneous operating conditions or approval.

## Validation

Expected backend suite: 65 tests (49 previous + 12 workspace orchestration
+ 4 new HTTP tests). Run from backend/:

    .venv-py312\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v

The 12 new orchestration tests passed in the assistant environment with
mocked checks, ranker and ChipSpec validation, and lightweight import stubs
for unavailable project dependencies. They do not establish real matcher
integration. The four HTTP tests use real project code but were NOT run
there because FastAPI is unavailable. Frontend build/browser checks are
also NOT run there. No complete-suite or actual-catalog pass is claimed.

Rebuild frontend/ with npm run build, restart backend, then hard-refresh.
Upload ST workbook, select STM32F051C6T6, Use this part, and run matching.
Check source USB remains Unknown, source/provenance are retained, changing
requirements clears stale results, a 72 MHz requirement rejects 48 MHz
candidates, and clearing/closing removes active results. Check both master
catalog files are unchanged. No package/dependency updates are included.

Existing CSV/manual imports still write the legacy catalog. Keep this pilot
on localhost; authenticated personal storage, hosted hardening and export
remain separate work.
