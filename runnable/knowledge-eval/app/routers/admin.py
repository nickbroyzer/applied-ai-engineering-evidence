"""Admin gate stand-in.

Production resolves the caller through Supabase JWT verification and then
checks `is_admin`: no credentials is a 401, credentials without the admin flag
is a 403. This package has no auth provider, so the dependency keeps the same
name, signature and refusal codes, and the tests override it to supply a
caller — which is how the production suite exercises this route too. The point
under test is that the CX index is reachable ONLY behind this gate, never how
the gate authenticates.
"""
from fastapi import HTTPException, status


def require_admin():
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
