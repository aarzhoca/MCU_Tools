"""Stateless matching of one uploaded source record; never saves catalogs."""
import math
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .requirement_schemas import Requirement
from .requirement_matching import _checks
from .models import ChipSpec

BASE_FIELDS = ("cpu_freq_mhz", "gpio", "flash_kb", "ram_kb", "package", "package_size_mm2")
EXTRA_FIELDS = ("core", "uart", "spi", "i2c", "usb", "usb_hs", "can", "can_fd", "ethernet", "crypto", "adc_bits", "adc_channels", "temp_max_c", "vcc_min")


class WorkspaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: dict[str, Any] = Field(max_length=80)
    characteristics: list[Literal["cpu_freq_mhz", "gpio", "flash_kb", "ram_kb", "core", "uart", "spi", "i2c", "usb", "usb_hs", "can", "can_fd", "ethernet", "crypto", "adc_bits", "adc_channels", "temp_max_c", "vcc_min"]] = Field(default_factory=lambda: ["cpu_freq_mhz", "flash_kb", "ram_kb"], max_length=20)
    requirements: list[Requirement] = Field(default_factory=list, max_length=100)
    top_k: int = Field(default=5, ge=1, le=20, strict=True)

    @model_validator(mode="after")
    def validate_source(self):
        name = self.source.get("part_number")
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise ValueError("Uploaded source needs an exact part number")
        # Prevent NaN/Infinity or non-JSON objects entering preserved metadata.
        import json
        try:
            json.dumps(self.source, allow_nan=False)
        except (ValueError, TypeError):
            raise ValueError("Uploaded source must contain finite JSON data")
        return self


def known(record, field):
    quality = record.get("field_quality", {})
    if not isinstance(quality, dict) or quality.get(field, "catalog") not in ("catalog", "verified"):
        return False
    value = record.get(field)
    if field in ("package", "core"):
        return isinstance(value, str) and bool(value.strip())
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and value >= 0 and (field != "package_size_mm2" or value > 0)
    except OverflowError:
        return False


def match_workspace(request, catalog, ranker, core_ranks):
    source = request.source
    missing = [field for field in BASE_FIELDS if not known(source, field)]
    if missing:
        raise ValueError("Cannot rank: uploaded source has unknown base fields: " + ", ".join(missing))
    extras = list(dict.fromkeys(key for key in request.characteristics if key in EXTRA_FIELDS))
    omitted = [key for key in extras if not known(source, key) or
               (key == "core" and source.get(key) not in core_ranks)]
    selected = [key for key in dict.fromkeys(request.characteristics) if key not in omitted]
    effective = list(BASE_FIELDS) + [key for key in extras if key not in omitted]
    rules = [rule.model_dump() for rule in request.requirements]
    ranked, failed, unknown, unranked = [], [], [], []
    counts = {"PASS": 0, "FAIL": 0, "UNKNOWN": 0, "NOT_EVALUATED": 0}
    for candidate in catalog:
        checked = _checks(candidate, rules)
        status = checked["eligibility"]
        counts[status] += 1
        diagnostic = {"part_number": candidate.get("part_number", "(missing)"),
                      "eligibility": status, "requirement_checks": checked["checks"]}
        if status == "FAIL":
            failed.append(diagnostic)
            continue
        if status == "UNKNOWN":
            unknown.append(diagnostic)
            continue
        missing = [field for field in effective if not known(candidate, field)]
        if "core" in effective and candidate.get("core") not in core_ranks:
            missing.append("recognized_core")
        if missing:
            unranked.append({**diagnostic, "reason": "Unknown ranking fields: " + ", ".join(missing)})
            continue
        try:
            ChipSpec(**candidate)
        except ValueError:
            unranked.append({**diagnostic, "reason": "Candidate does not satisfy legacy matcher schema"})
            continue
        match = ranker(source, [candidate], selected, top_k=1)[0]
        # Preserve raw candidate values instead of exposing model-inserted defaults.
        ranked.append({"part_number": candidate["part_number"], "similarity_pct": match.similarity_pct,
            "score": match.score, "eligibility": status, "requirement_checks": checked["checks"],
            "comparison": [row.model_dump() for row in match.comparison]})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return {"source": source, "requirements_used": rules, "omitted_source_fields": omitted,
        "ranking_mode": "existing-matcher-with-explicit-base-data", "eligibility_counts": counts,
        "ranked_count": len(ranked), "unranked_count": len(unranked),
        "matches": ranked[:request.top_k], "failed_candidates": failed[:request.top_k],
        "unknown_candidates": unknown[:request.top_k], "unranked_candidates": unranked[:request.top_k],
        "temporary": True, "message": None if ranked else "No rankable candidates for the checked requirements and available data."}
