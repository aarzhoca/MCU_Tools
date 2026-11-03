# Mandatory requirements API (development branch)

POST /api/match accepts the existing fields plus optional `requirements`:

```json
{"part_number":"STM32F051C6T6","characteristics":["flash_kb"],"top_k":5,
 "requirements":[{"field":"cpu_freq_mhz","operator":"gte","value":48}]}
```

- Numeric rules accept gte/lte/eq; package and core accept exact eq only.
- Numeric values must be JSON numbers, not strings or booleans.
- At most 100 requirements; top_k must be an integer from 1 to 100.
  These bounds also apply to legacy requests (intentional validation tightening).
- Omitted or empty requirements preserve the legacy ranker call and scores.
  Additive response fields mark those results NOT_EVALUATED.
- With requirements, the entire raw catalog is evaluated before result limits.
  Only PASS records are ranked. FAIL/UNKNOWN records are not sent to the ranker.
- failed_candidates/unknown_candidates contain part numbers and explanations,
  in catalog order, limited separately by top_k; eligibility_counts are totals.
- Empty passing results never trigger automatic requirement relaxation.
- Legacy meets_all retains its old meaning; use eligibility for mandatory checks.
- Catalog values without field_quality are labelled catalog, not verified.
  PASS is conditional on those values, not independent datasheet approval.
- Missing temp_min_c is UNKNOWN; no lower temperature is inferred.
- Package area is not a width/height or pin-compatibility check.
- The existing fuzzy source lookup and ranking approximations remain unchanged.
- Existing matcher/ChipSpec validity requirements still apply to passing records.
- Frontend controls, dataset verification, upload isolation and export are not
  implemented by this backend change.

## Tests

From backend/, install `pip install -r requirements-dev.txt`, then run:

```text
python -m unittest discover -s tests -p "test_*.py" -v
```

The HTTP tests use the real matcher with synthetic data and mocked catalog I/O.
In the assistant environment only the 10 schema/orchestration tests were run
(Pydantic 2.11.4, injected ranker). FastAPI/Starlette were unavailable. The five
HTTP tests, pinned Pydantic 2.9.2 environment, and actual catalog remain untested.
