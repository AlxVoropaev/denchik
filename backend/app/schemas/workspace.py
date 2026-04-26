from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class WorkspaceOut(BaseModel):
    id: int
    name: str
    owner_id: int

    model_config = {"from_attributes": True}


class MemberAdd(BaseModel):
    user_id: int
    role: str = "member"
