"""ML API — FastAPI endpoints for questionnaire validation.

Provides REST API for the frontend/backend to validate user questionnaires
instantly using the ML model.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .questionnaire_validator import ValidationStatus, validate_questionnaire

router = APIRouter(prefix="/ml", tags=["ml"])


class QuestionnaireInput(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    position: str = ""
    experience: str = ""
    skills: str = ""
    bio: str = ""
    education: str = ""


class ValidationResponse(BaseModel):
    status: str
    confidence: float
    score: int
    reasons: list[str]
    suggestions: list[str]
    approved: bool


@router.post("/validate-questionnaire", response_model=ValidationResponse)
async def validate_user_questionnaire(data: QuestionnaireInput):
    """Instantly validate a user registration questionnaire.
    
    Returns validation result with score, status, and suggestions.
    Score >= 70: auto-approved
    Score 40-69: needs manual review
    Score < 40: rejected with suggestions
    """
    result = validate_questionnaire(data.model_dump())
    return ValidationResponse(
        status=result.status.value,
        confidence=result.confidence,
        score=result.score,
        reasons=result.reasons,
        suggestions=result.suggestions,
        approved=result.status == ValidationStatus.APPROVED,
    )


@router.get("/health")
async def ml_health():
    """Health check for ML service."""
    return {"status": "ok", "model": "questionnaire_validator", "version": "1.0.0"}
