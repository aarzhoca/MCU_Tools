from fastapi import APIRouter, HTTPException

from ..data_loader import find_competitor_part, search_competitor_parts, get_nuvoton_parts
from ..matcher import find_matches
from ..requirement_schemas import RequirementsMatchRequest, RequirementsMatchResponse
from ..requirement_matching import match_with_requirements

router = APIRouter(prefix="/api", tags=["match"])


@router.post("/match", response_model=RequirementsMatchResponse)
def match_part(req: RequirementsMatchRequest):
    competitor = find_competitor_part(req.part_number)
    if not competitor:
        suggestions = search_competitor_parts(req.part_number)
        suggestion_text = ""
        if suggestions:
            names = ", ".join(s["part_number"] for s in suggestions[:3])
            suggestion_text = f" Did you mean: {names}?"
        raise HTTPException(
            status_code=404,
            detail=f"Part '{req.part_number}' not found in the catalog.{suggestion_text}"
        )

    return match_with_requirements(
        competitor, get_nuvoton_parts(), req, ranker=find_matches,
    )
