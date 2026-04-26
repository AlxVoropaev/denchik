from pydantic import BaseModel, Field


class LabelCreate(BaseModel):
    workspace_id: int
    name: str = Field(min_length=1, max_length=64)
    color: str = "#888888"


class LabelOut(BaseModel):
    id: int
    workspace_id: int
    name: str
    color: str

    model_config = {"from_attributes": True}
