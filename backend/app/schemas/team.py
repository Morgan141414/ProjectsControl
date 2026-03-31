from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TeamRole


class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    project_id: str | None = None


class TeamMemberInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: str
    role: TeamRole
    full_name: str | None = None


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    project_id: str | None
    name: str
    members: list[TeamMemberInfo] = []


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    project_id: str | None = None


class TeamMemberAdd(BaseModel):
    user_id: str
    role: TeamRole | None = None
