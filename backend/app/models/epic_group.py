from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class EpicGroup(Base):
    __tablename__ = "epic_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    epics: Mapped[list["Epic"]] = relationship(  # noqa: F821
        back_populates="group", cascade="all, delete-orphan", order_by="Epic.position"
    )
