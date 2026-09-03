"""Shared block-relationship helpers used across routers and feeds."""
import uuid

from sqlalchemy import exists, or_
from sqlalchemy.orm import Session

from app.models import BlockedUser

# Raw-SQL WHERE fragment for the nearby feed.
# Excludes listings whose giver has any block relationship with the viewer.
# Requires a :viewer_id bind parameter.
NEARBY_BLOCK_FILTER_SQL = (
    "giver_id NOT IN ("
    "SELECT blocked_id FROM blocked_users WHERE blocker_id = :viewer_id "
    "UNION "
    "SELECT blocker_id FROM blocked_users WHERE blocked_id = :viewer_id"
    ")"
)


def is_blocked(db: Session, user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> bool:
    """Return True if a block row exists in either direction between user_a and user_b."""
    if user_a_id == user_b_id:
        return False
    return db.query(
        exists().where(
            or_(
                (BlockedUser.blocker_id == user_a_id) & (BlockedUser.blocked_id == user_b_id),
                (BlockedUser.blocker_id == user_b_id) & (BlockedUser.blocked_id == user_a_id),
            )
        )
    ).scalar()


def block_exists_expr(viewer_id: uuid.UUID, other_id_column):
    """SQLAlchemy boolean EXISTS expression for use in ORM .filter(~block_exists_expr(...)).

    other_id_column is a mapped column, e.g. Listing.giver_id.
    """
    return exists().where(
        or_(
            (BlockedUser.blocker_id == viewer_id) & (BlockedUser.blocked_id == other_id_column),
            (BlockedUser.blocker_id == other_id_column) & (BlockedUser.blocked_id == viewer_id),
        )
    )
