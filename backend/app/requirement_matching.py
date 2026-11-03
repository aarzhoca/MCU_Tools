"""Filter raw catalog records before ranking or truncating results."""
import math
from .requirement_schemas import CheckedMatch, RequirementsMatchResponse
from .requirements import evaluate_requirements


def _checks(candidate, rules):
    # Malformed quality labels cannot accidentally establish a mandatory pass.
    raw_quality = candidate.get("field_quality", {})
    quality = raw_quality if isinstance(raw_quality, dict) else {}
    clean = dict(candidate)
    clean["field_quality"] = {
        rule["field"]: quality.get(rule["field"], "catalog")
        if isinstance(quality.get(rule["field"], "catalog"), str) and isinstance(raw_quality, dict)
        else "unknown" for rule in rules
    }
    result = evaluate_requirements(clean, rules)
    for check in result["checks"]:
        value = check["actual_value"]
        if not isinstance(value, (str, int, float, bool, type(None))):
            check["actual_value"] = None
        elif isinstance(value, float) and not math.isfinite(value):
            check["actual_value"] = None
    return result


def match_with_requirements(competitor, catalog, request, ranker):
    rules = [rule.model_dump() for rule in request.requirements]
    if not rules:
        matches = ranker(competitor, catalog, request.characteristics, top_k=request.top_k)
        return RequirementsMatchResponse(
            competitor_part=competitor,
            matches=[CheckedMatch(**match.model_dump()) for match in matches],
            characteristics_used=request.characteristics,
        )

    passing, evaluations = [], []
    failed, unknown = [], []
    for candidate in catalog:
        result = _checks(candidate, rules)
        if result["eligibility"] == "PASS":
            passing.append(candidate)
            evaluations.append(result)
        else:
            target = failed if result["eligibility"] == "FAIL" else unknown
            target.append(dict(part_number=candidate["part_number"],
                eligibility=result["eligibility"], requirement_checks=result["checks"]))
    matches = []
    # Rank individually to retain raw-record evidence even for duplicate part names.
    for candidate, result in zip(passing, evaluations):
        ranked = ranker(competitor, [candidate], request.characteristics, top_k=1)
        for match in ranked:
            matches.append(CheckedMatch(**match.model_dump(), eligibility="PASS",
                requirement_checks=result["checks"]))
    matches.sort(key=lambda item: item.score, reverse=True)
    return RequirementsMatchResponse(
        competitor_part=competitor, matches=matches[:request.top_k],
        characteristics_used=request.characteristics, requirements_used=request.requirements,
        failed_candidates=failed[:request.top_k], unknown_candidates=unknown[:request.top_k],
        eligibility_counts={"PASS": len(passing), "FAIL": len(failed), "UNKNOWN": len(unknown)},
        message=None if passing else "No candidate meets all checked mandatory requirements.",
    )
