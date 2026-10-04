"""Admin actions — suspend, lift and time out a user's standing."""
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import User
from app.routers.admin import require_admin
from app.services.standing_notices import notify, record_action
from app.utils.iso import iso_utc

router = APIRouter(tags=["admin-actions"])


class AdminActionBody(BaseModel):
    reason: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason must not be blank")
        return stripped


class AdminTimeoutBody(AdminActionBody):
    days: int = Field(default=7, ge=1, le=90)


def first_name(user: User) -> str:
    parts = (user.display_name or "").split()
    return parts[0] if parts else "there"


def _refuse_admin_target(user: User) -> None:
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin account cannot be suspended or timed out",
        )


def _standing(user: User) -> dict[str, Any]:
    if user.is_suspended:
        standing = "suspended"
    elif user.picker_timeout_until is not None and user.picker_timeout_until > datetime.utcnow():
        standing = "timeout"
    else:
        standing = "ok"
    return {
        "id": str(user.id),
        "standing": standing,
        "timeout_until": iso_utc(user.picker_timeout_until),
        "suspension_reason": user.suspension_reason,
    }


@router.post("/admin/users/{user_id}/suspend")
def suspend_user(
    user_id: uuid.UUID,
    body: AdminActionBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _refuse_admin_target(user)
    if user.is_suspended:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already suspended")

    user.is_suspended = True
    user.suspension_reason = body.reason
    db.add(user)
    action_row = record_action(db, actor=current_user, subject=user, action="suspend", reason=body.reason)
    db.commit()
    db.refresh(user)
    db.refresh(action_row)

    notice_sent = notify(
        db,
        action_row,
        user,
        heading="Account disabled",
        paragraphs=[f"Hi {first_name(user)},", body.reason],
    )
    return {**_standing(user), "notice_sent": notice_sent}


@router.post("/admin/users/{user_id}/lift")
def lift_user(
    user_id: uuid.UUID,
    body: AdminActionBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_suspended and user.picker_timeout_until is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already in good standing")

    user.is_suspended = False
    user.suspension_reason = None
    user.picker_timeout_until = None
    db.add(user)
    action_row = record_action(db, actor=current_user, subject=user, action="lift", reason=body.reason)
    db.commit()
    db.refresh(user)
    db.refresh(action_row)

    notice_sent = notify(
        db,
        action_row,
        user,
        heading="Account restored",
        paragraphs=[f"Hi {first_name(user)},", body.reason],
    )
    return {**_standing(user), "notice_sent": notice_sent}


@router.post("/admin/users/{user_id}/timeout")
def timeout_user(
    user_id: uuid.UUID,
    body: AdminTimeoutBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _refuse_admin_target(user)
    if user.is_suspended:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is suspended; lift first")

    user.picker_timeout_until = datetime.utcnow() + timedelta(days=body.days)
    db.add(user)
    action_row = record_action(db, actor=current_user, subject=user, action="timeout", reason=body.reason)
    db.commit()
    db.refresh(user)
    db.refresh(action_row)

    notice_sent = notify(
        db,
        action_row,
        user,
        heading=f"Claims paused for {body.days} days",
        paragraphs=[
            f"Hi {first_name(user)},",
            body.reason,
            f"You can claim again from {user.picker_timeout_until:%b %-d, %Y}.",
        ],
    )
    return {**_standing(user), "notice_sent": notice_sent}
