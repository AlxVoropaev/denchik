from pydantic import BaseModel, Field


class EpicGroupCreate(BaseModel):
    workspace_id: int
    name: str = Field(min_length=1, max_length=120)


class EpicGroupOut(BaseModel):
    id: int
    workspace_id: int
    name: str
    position: int

    model_config = {"from_attributes": True}


class EpicCreate(BaseModel):
    epic_group_id: int
    name: str = Field(min_length=1, max_length=120)


class EpicOut(BaseModel):
    id: int
    epic_group_id: int
    name: str
    position: int

    model_config = {"from_attributes": True}


class EpicUpdate(BaseModel):
    name: str | None = None
    position: int | None = None
    epic_group_id: int | None = None
