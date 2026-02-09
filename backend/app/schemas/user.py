from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    bio: str | None = None
    specialty: str | None = None
    avatar_url: str | None = None
    socials_json: str | None = None


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    bio: str | None = None
    specialty: str | None = None
    avatar_url: str | None = None
    socials_json: str | None = None
