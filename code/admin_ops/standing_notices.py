"""Recording and notifying users of admin/automatic standing actions."""
import logging

from sqlalchemy.orm import Session

from app.models import AdminAction, User
from app.services.email_service import send_email
from app.services.email_templates import branded_email

logger = logging.getLogger(__name__)


def record_action(
    db: Session,
    *,
    actor: User | None,
    subject: User,
    action: str,
    reason: str,
) -> AdminAction:
    action_row = AdminAction(
        actor_user_id=actor.id if actor is not None else None,
        subject_user_id=subject.id,
        action=action,
        reason=reason,
        notice_sent=False,
    )
    db.add(action_row)
    return action_row


def send_branded(
    db: Session,
    *,
    actor: User | None,
    subject_user: User,
    action: str,
    reason: str,
    heading: str,
    paragraphs: list[str],
    to_email: str | None = None,
    reference: str | None = None,
    subject: str | None = None,
) -> tuple[AdminAction, bool]:
    row = record_action(db, actor=actor, subject=subject_user, action=action, reason=reason)
    db.flush()

    recipient = to_email if to_email is not None else subject_user.email

    sent = False
    if recipient:
        html_body, text_body = branded_email(
            heading=heading,
            paragraphs=paragraphs,
            reference=reference if reference is not None else str(row.id)[:8].upper(),
        )
        try:
            send_email(
                to=recipient,
                subject=subject if subject is not None else heading,
                html=html_body,
                text=text_body,
            )
            sent = True
        except Exception as exc:
            logger.warning(
                "admin action notice failed to send: action_id=%s exc_class=%s",
                row.id,
                type(exc).__name__,
            )

    if sent:
        row.notice_sent = True

    return row, sent


def notify(
    db: Session,
    action_row: AdminAction,
    user: User,
    *,
    heading: str,
    paragraphs: list[str],
) -> bool:
    if user.deleted_at is not None or not user.email:
        return False

    html_body, text_body = branded_email(
        heading=heading,
        paragraphs=paragraphs,
        reference=str(action_row.id)[:8].upper(),
    )

    try:
        send_email(to=user.email, subject=heading, html=html_body, text=text_body)
    except Exception as exc:
        logger.warning(
            "admin action notice failed to send: action_id=%s exc_class=%s",
            action_row.id,
            type(exc).__name__,
        )
        return False

    action_row.notice_sent = True
    db.commit()
    return True
