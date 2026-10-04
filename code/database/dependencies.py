import datetime
import logging
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException, Request
from jwt import PyJWKClient, PyJWKClientError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.utils.client_ip import client_ip
from app.utils.geoip import country_for_ip

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient:
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    # Validate-and-add timeout: PyJWT 2.8.0 may or may not expose a timeout kwarg
    # on PyJWKClient. Try the kwarg path; fall back to no-timeout construction
    # if TypeError is raised. Do not subclass or monkey-patch.
    try:
        return PyJWKClient(jwks_url, cache_keys=True, lifespan=300, timeout=5)
    except TypeError:
        return PyJWKClient(jwks_url, cache_keys=True, lifespan=300)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ")

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            leeway=datetime.timedelta(seconds=10),
        )
    except jwt.ExpiredSignatureError:
        logger.warning("[JWT VERIFY] token expired")
        raise HTTPException(
            status_code=401,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning("[JWT VERIFY] invalid token: %s", type(e).__name__)
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except PyJWKClientError as e:
        logger.warning("[JWT VERIFY] JWKS lookup failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Auth temporarily unavailable",
        )
    except Exception as e:
        logger.warning("[JWT VERIFY] unexpected: %s", type(e).__name__)
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == sub).first()
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.deleted_at is not None:
        raise HTTPException(
            status_code=403,
            detail="Account deleted",
            headers={"X-Zelbi-Reason": "account_deleted"},
        )

    if user.is_suspended:
        raise HTTPException(
            status_code=403,
            detail=user.suspension_reason or "Account suspended",
            headers={"X-Zelbi-Reason": "account_suspended"},
        )

    if user.signup_country_checked_at is None:
        ip = client_ip(request)
        country = country_for_ip(ip) if ip else None
        if country is not None:
            try:
                user.signup_country = country
                user.signup_country_checked_at = datetime.datetime.utcnow()
                db.commit()
            except Exception as e:
                logger.warning("[COUNTRY] failed to stamp signup_country: %s", e)
                db.rollback()

    if user.signup_country is not None and user.signup_country != "US":
        raise HTTPException(
            status_code=403,
            detail="Not available in your country",
            headers={"X-Zelbi-Reason": "country_not_supported"},
        )

    try:
        now = datetime.datetime.utcnow()
        if user.last_active_at is None or (now - user.last_active_at).total_seconds() > 60:
            user.last_active_at = now
            db.commit()
    except Exception as e:
        logger.warning("[ACTIVITY] failed to update last_active_at: %s", e)
        db.rollback()

    return user


def get_current_user_detached(
    request: Request,
    authorization: str | None = Header(default=None),
) -> User:
    """Authenticate, then RELEASE the connection before the endpoint body runs.

    Depends(get_db) keeps its session open for the whole request, so an endpoint
    that authenticates and then makes a slow external call holds a pooler
    connection for the entire duration of that call. The AI endpoints wait
    several seconds on the Anthropic API, so they use this instead: the session
    is opened, the user is loaded and expunged, and the connection goes back to
    the pool before the model call starts. Safe because SessionLocal is built
    with expire_on_commit=False, so the expunged User keeps its loaded columns.

    Only for endpoints that need NO database access after authentication.
    """
    db = SessionLocal()
    try:
        user = get_current_user(request=request, authorization=authorization, db=db)
        db.expunge(user)
        return user
    finally:
        db.close()


def get_current_user_optional(
    request: Request,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return get_current_user(request=request, authorization=authorization, db=db)
    except HTTPException:
        return None
