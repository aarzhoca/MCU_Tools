"""Additive API schemas; legacy models and ranking semantics are unchanged."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr, model_validator
from .models import MatchRequest, MatchResponse, MatchResult
from .requirements import evaluate_requirements


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    operator: Literal["gte", "lte", "eq"]
    value: StrictInt | StrictFloat | StrictStr

    @model_validator(mode="after")
    def validate_rule(self):
        evaluate_requirements({}, [self.model_dump()])
        return self


class RequirementsMatchRequest(MatchRequest):
    top_k: int = Field(default=5, ge=1, le=100, strict=True)
    requirements: list[Requirement] = Field(default_factory=list, max_length=100)


class RequirementCheck(BaseModel):
    field: str
    operator: Literal["gte", "lte", "eq"]
    required_value: int | float | str
    actual_value: Any = None
    evidence: str
    status: Literal["PASS", "FAIL", "UNKNOWN"]
    reason: str


class CheckedMatch(MatchResult):
    eligibility: Literal["PASS", "NOT_EVALUATED"] = "NOT_EVALUATED"
    requirement_checks: list[RequirementCheck] = Field(default_factory=list)


class CandidateDiagnostic(BaseModel):
    part_number: str
    eligibility: Literal["FAIL", "UNKNOWN"]
    requirement_checks: list[RequirementCheck]


class RequirementsMatchResponse(MatchResponse):
    matches: list[CheckedMatch]
    requirements_used: list[Requirement] = Field(default_factory=list)
    failed_candidates: list[CandidateDiagnostic] = Field(default_factory=list)
    unknown_candidates: list[CandidateDiagnostic] = Field(default_factory=list)
    eligibility_counts: dict[str, int] = Field(default_factory=dict)
    message: str | None = None
