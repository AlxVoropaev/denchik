from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Epic(Base):
    __tablename__ = "epics"

    id: Mapped[int] = mapped_column(primary_key=True)
    epic_group_id: Mapped[int] = mapped_column(
        ForeignKey("epic_groups.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    group: Mapped["EpicGroup"] = relationship(back_populates="epics")  # noqa: F821
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        back_populates="epic", cascade="all, delete-orphan", order_by="Task.position"
    )
