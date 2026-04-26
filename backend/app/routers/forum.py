from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

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
    # 1. Epic group + its epics in a single round-trip via selectinload.
    group_res = await session.execute(
        select(EpicGroup)
        .where(EpicGroup.id == epic_group_id)
        .options(selectinload(EpicGroup.epics))
    )
    group = group_res.scalar_one_or_none()
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Epic group not found")
    await require_workspace_member(group.workspace_id, session, user)

    # `EpicGroup.epics` is already ordered by Epic.position via the
    # relationship; mirror that here as the response contract.
    epics = sorted(group.epics, key=lambda e: (e.position, e.id))
    epic_ids = [e.id for e in epics]

    if not epic_ids:
        return ForumView(epic_group_id=group.id, name=group.name, subforums=[])

    # 2. All tasks for those epics in one query, ordered for the response.
    tasks_res = await session.execute(
        select(Task)
        .where(Task.epic_id.in_(epic_ids))
        .order_by(Task.epic_id, Task.updated_at.desc(), Task.id)
    )
    tasks = list(tasks_res.scalars().all())
    tasks_by_epic: dict[int, list[Task]] = defaultdict(list)
    for task in tasks:
        tasks_by_epic[task.epic_id].append(task)
    task_ids = [t.id for t in tasks]

    # 3. Comment count + last-comment timestamp per task in one aggregate.
    comment_stats: dict[int, tuple[int, datetime | None]] = {}
    last_authors: dict[int, int | None] = {}
    if task_ids:
        agg_res = await session.execute(
            select(
                Comment.task_id,
                func.count(Comment.id).label("c"),
                func.max(Comment.created_at).label("last_at"),
            )
            .where(Comment.task_id.in_(task_ids))
            .group_by(Comment.task_id)
        )
        for task_id, count, last_at in agg_res.all():
            comment_stats[task_id] = (int(count), last_at)

        # Resolve the author of the most-recent comment per task. We do this
        # in one statement using a correlated subquery on `created_at`.
        if comment_stats:
            tasks_with_comments = list(comment_stats.keys())
            last_at_subq = (
                select(func.max(Comment.created_at))
                .where(Comment.task_id == Task.id)
                .correlate(Task)
                .scalar_subquery()
            )
            authors_res = await session.execute(
                select(Comment.task_id, Comment.author_id)
                .join(Task, Task.id == Comment.task_id)
                .where(
                    Comment.task_id.in_(tasks_with_comments),
                    Comment.created_at == last_at_subq,
                )
            )
            for task_id, author_id in authors_res.all():
                # If two comments share the same created_at, last writer wins —
                # acceptable for forum-ordering purposes.
                last_authors[task_id] = author_id

    # 4. Walk the in-memory structures to assemble the response.
    subforums: list[ForumSubforum] = []
    for epic in epics:
        topics: list[ForumTopic] = []
        for task in tasks_by_epic.get(epic.id, []):
            count, last_at = comment_stats.get(task.id, (0, None))
            topics.append(
                ForumTopic(
                    task_id=task.id,
                    title=task.title,
                    author_id=task.author_id,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    comment_count=count,
                    last_comment_author_id=last_authors.get(task.id),
                    last_comment_at=last_at,
                )
            )
        subforums.append(
            ForumSubforum(
                epic_id=epic.id, name=epic.name, position=epic.position, topics=topics
            )
        )

    return ForumView(epic_group_id=group.id, name=group.name, subforums=subforums)
