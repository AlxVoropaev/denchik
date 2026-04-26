from datetime import datetime

from pydantic import BaseModel


class AttachmentOut(BaseModel):
    id: int
    task_id: int
    uploaded_by: int
    filename: str
    content_type: str
    size: int
    created_at: datetime

    model_config = {"from_attributes": True}
