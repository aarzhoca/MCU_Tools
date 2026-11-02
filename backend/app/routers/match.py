from fastapi import APIRouter, HTTPException

from ..data_loader import find_competitor_part, search_competitor_parts, get_nuvoton_parts
from ..matcher import find_matches
from ..models import MatchRequest, MatchResponse

router = APIRouter(prefix="/api", tags=["match"])


@router.post("/match", response_model=MatchResponse)
def match_part(req: MatchRequest):
    competitor = find_competitor_part(req.part_number)
    if not competitor:
        # Suggest close matches to help the user
        suggestions = search_competitor_parts(req.part_number)
        suggestion_text = ""
        if suggestions:
            names = ", ".join(s["part_number"] for s in suggestions[:3])
            suggestion_text = f" Did you mean: {names}?"
        raise HTTPException(
            status_code=404,
            detail=f"Part '{req.part_number}' not found in the catalog.{suggestion_text}"
        )

    nuvoton_catalog = get_nuvoton_parts()
    matches = find_matches(competitor, nuvoton_catalog, req.characteristics, top_k=req.top_k)

    return MatchResponse(
        competitor_part=competitor,
        matches=matches,
        characteristics_used=req.characteristics,
    )
