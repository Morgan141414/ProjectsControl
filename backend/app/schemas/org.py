from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import JoinStatus


class OrgCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class OrgResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    join_code: str


class JoinRequestCreate(BaseModel):
    org_code: str = Field(min_length=4, max_length=16)


class JoinRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    user_id: str
    status: JoinStatus
