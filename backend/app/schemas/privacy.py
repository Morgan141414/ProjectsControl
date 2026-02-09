from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MatchType, PrivacyAction, PrivacyTarget


class PrivacyRuleCreate(BaseModel):
    target: PrivacyTarget
    match_type: MatchType
    pattern: str = Field(min_length=1, max_length=500)
    action: PrivacyAction
    enabled: bool = True


class PrivacyRuleUpdate(BaseModel):
    pattern: str | None = Field(default=None, min_length=1, max_length=500)
    action: PrivacyAction | None = None
    enabled: bool | None = None


class PrivacyRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    target: PrivacyTarget
    match_type: MatchType
    pattern: str
    action: PrivacyAction
    enabled: bool
