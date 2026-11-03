"""Apply explicit, sourced minimum-temperature corrections to loaded records.

Never writes catalogs. Conflicting existing values are preserved and flagged
unverified. This is not a family-wide temperature default.
"""
from copy import deepcopy


def apply_catalog_corrections(parts, corrections):
    result = deepcopy(parts)
    for correction in corrections:
        if correction.get("field") != "temp_min_c":
            raise ValueError("Only explicit minimum-temperature corrections are supported")
        value = correction.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Correction must have a numeric temperature")
        import math
        if not math.isfinite(value):
            raise ValueError("Correction temperature must be finite")
        source = correction.get("source")
        if not isinstance(source, dict) or not source.get("url") or not source.get("quote"):
            raise ValueError("Correction needs a source URL and supporting quote")
        target = correction["part_number"].strip().upper()
        for part in result:
            if part.get("part_number", "").strip().upper() != target:
                continue
            field = correction["field"]
            quality = dict(part.get("field_quality") or {})
            if part.get(field) is not None and part[field] != value:
                quality[field] = "unverified"
                conflicts = list(part.get("catalog_correction_conflicts") or [])
                conflict = {"field": field, "existing_value": part[field],
                            "proposed_value": value, "source": deepcopy(source)}
                if conflict not in conflicts:
                    conflicts.append(conflict)
                part["catalog_correction_conflicts"] = conflicts
            else:
                part[field] = value
                quality[field] = "verified"
                sources = dict(part.get("field_sources") or {})
                sources[field] = deepcopy(source)
                part["field_sources"] = sources
            part["field_quality"] = quality
    return result
