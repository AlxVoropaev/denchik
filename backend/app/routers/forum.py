from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, SessionDep, require_workspace_member
from app.models.comment import Comment
from app.models.epic import Epic
from app.models.epic_group import EpicGroup
from app.models.task import Task
from app.schemas.forum import ForumSubforum, ForumTopic, ForumView

router = APIRouter(tags=["forum"])


@router.get("/forum/{epic_group_id}", response_model=ForumView)
async def forum_view(
    epic_group_id: int, user: CurrentUser, session: SessionDep
) -> ForumView:
    group = await session.get(EpicGroup, epic_group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Epic group not found")
    await require_workspace_member(group.workspace_id, session, user)

    epics_res = await session.execute(
        select(Epic).where(Epic.epic_group_id == epic_group_id).order_by(Epic.position, Epic.id)
    )
    epics = list(epics_res.scalars().all())

    subforums: list[ForumSubforum] = []
    for epic in epics:
        tasks_res = await session.execute(
            select(Task).where(Task.epic_id == epic.id).order_by(Task.updated_at.desc())
        )
        tasks = list(tasks_res.scalars().all())
        topics: list[ForumTopic] = []
        for task in tasks:
            cnt_res = await session.execute(
                select(func.count(Comment.id)).where(Comment.task_id == task.id)
            )
            count = int(cnt_res.scalar_one())
            last_res = await session.execute(
                select(Comment)
                .where(Comment.task_id == task.id)
                .order_by(Comment.created_at.desc())
                .limit(1)
            )
            last = last_res.scalar_one_or_none()
            topics.append(
                ForumTopic(
                    task_id=task.id,
                    title=task.title,
                    author_id=task.author_id,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    comment_count=count,
                    last_comment_author_id=last.author_id if last else None,
                    last_comment_at=last.created_at if last else None,
                )
            )
        subforums.append(
            ForumSubforum(epic_id=epic.id, name=epic.name, position=epic.position, topics=topics)
        )

    return ForumView(epic_group_id=group.id, name=group.name, subforums=subforums)
