"""Mandatory checks on raw catalog records; independent of similarity ranking.

Missing/null and explicitly unverified fields are UNKNOWN. Numeric values
must be finite and nonnegative, except temperatures. No package estimates
or core hierarchy are used to establish mandatory compatibility.
"""
import math
from numbers import Real

NUMERIC_FIELDS = frozenset({
    "cpu_freq_mhz", "flash_kb", "ram_kb", "gpio", "adc_bits",
    "adc_channels", "uart", "spi", "i2c", "usb", "usb_hs", "can",
    "can_fd", "ethernet", "crypto", "vcc_min", "vcc_max",
    "temp_min_c", "temp_max_c", "package_size_mm2",
})
TEXT_FIELDS = frozenset({"core", "package"})
UNVERIFIED = frozenset({"estimated", "unknown", "unverified"})


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    try:
        return math.isfinite(value) and (field.startswith("temp_") or value >= 0)
    except (OverflowError, TypeError):
        return False


def evaluate_requirements(candidate, requirements):
    """Evaluate required checks only; validate inputs before returning results.

    Requirement: {field, operator: gte/lte/eq, value}.
    Numeric fields accept gte/lte/eq; core and package accept exact eq only.
    Optional candidate field_quality maps field names to verified/estimated/
    unknown/unverified. Absent quality metadata means legacy catalog value,
    NOT independent datasheet verification. For Pydantic records, pass raw
    data or a dump excluding unset fields so defaults cannot mask missingness.
    This foundation does not yet modify /api/match.
    """
    requirements = list(requirements)
    for req in requirements:
        field, op, target = req.get("field"), req.get("operator"), req.get("value")
        if field in NUMERIC_FIELDS:
            if op not in {"gte", "lte", "eq"} or not _number(target, field):
                raise ValueError("Invalid numeric requirement: " + str(field))
        elif field in TEXT_FIELDS:
            if op != "eq" or not isinstance(target, str) or not target.strip():
                raise ValueError("Text requirements need a nonempty exact value")
        else:
            raise ValueError("Unsupported requirement field: " + str(field))

    quality = candidate.get("field_quality") or {}
    checks = []
    for req in requirements:
        field, op, target = req["field"], req["operator"], req["value"]
        actual = candidate.get(field)
        evidence = quality.get(field, "catalog")
        valid = (_number(actual, field) if field in NUMERIC_FIELDS
                 else isinstance(actual, str) and bool(actual.strip()))
        if evidence in UNVERIFIED or evidence not in {"catalog", "verified"} or not valid:
            status, reason = "UNKNOWN", "Missing, invalid, or unverified catalog value"
        else:
            if field in TEXT_FIELDS:
                passed = actual.strip().casefold() == target.strip().casefold()
            elif op == "gte":
                passed = actual >= target
            elif op == "lte":
                passed = actual <= target
            else:
                passed = actual == target
            status = "PASS" if passed else "FAIL"
            reason = "Catalog value satisfies requirement" if passed else "Catalog value violates requirement"
        checks.append({"field": field, "operator": op, "required_value": target,
                       "actual_value": actual, "evidence": evidence,
                       "status": status, "reason": reason})
    statuses = {check["status"] for check in checks}
    overall = ("FAIL" if "FAIL" in statuses else
               "UNKNOWN" if "UNKNOWN" in statuses else
               "PASS" if checks else "NOT_EVALUATED")
    return {"eligibility": overall, "checks": checks}
