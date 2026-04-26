from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, SessionDep, require_workspace_member
from app.models.comment import Comment
from app.models.epic import Epic
from app.models.epic_group import EpicGroup
from app.models.task import Task
from app.schemas.comment import CommentCreate, CommentOut

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["comments"])


async def _ws_for_task(session, task_id: int) -> tuple[Task, int]:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    epic = await session.get(Epic, task.epic_id)
    assert epic is not None
    group = await session.get(EpicGroup, epic.epic_group_id)
    assert group is not None
    return task, group.workspace_id


@router.get("", response_model=list[CommentOut])
async def list_comments(
    task_id: int, user: CurrentUser, session: SessionDep
) -> list[Comment]:
    _, ws_id = await _ws_for_task(session, task_id)
    await require_workspace_member(ws_id, session, user)
    res = await session.execute(
        select(Comment).where(Comment.task_id == task_id).order_by(Comment.created_at, Comment.id)
    )
    return list(res.scalars().all())


@router.post("", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(
    task_id: int, payload: CommentCreate, user: CurrentUser, session: SessionDep
) -> Comment:
    task, ws_id = await _ws_for_task(session, task_id)
    await require_workspace_member(ws_id, session, user)

    if payload.parent_comment_id is not None:
        parent = await session.get(Comment, payload.parent_comment_id)
        if parent is None or parent.task_id != task.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid parent comment")
        if parent.parent_comment_id is not None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Comments can be nested only one level deep"
            )

    comment = Comment(
        task_id=task.id,
        parent_comment_id=payload.parent_comment_id,
        author_id=user.id,
        body=payload.body,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return comment


@router.patch("/{comment_id}", response_model=CommentOut)
async def edit_comment(
    task_id: int,
    comment_id: int,
    payload: CommentCreate,
    user: CurrentUser,
    session: SessionDep,
) -> Comment:
    _, ws_id = await _ws_for_task(session, task_id)
    await require_workspace_member(ws_id, session, user)
    comment = await session.get(Comment, comment_id)
    if comment is None or comment.task_id != task_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found")
    if comment.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your comment")
    comment.body = payload.body
    comment.edited_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(comment)
    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    task_id: int, comment_id: int, user: CurrentUser, session: SessionDep
) -> None:
    _, ws_id = await _ws_for_task(session, task_id)
    await require_workspace_member(ws_id, session, user)
    comment = await session.get(Comment, comment_id)
    if comment is None or comment.task_id != task_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found")
    if comment.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your comment")
    await session.delete(comment)
    await session.commit()
