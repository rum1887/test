"""
Administrative Authentication and Control Plane Protection Dependency.
Enforces administrative authorization token on sensitive control routes:
- /api/gateway/toggle-guard
- /api/scenarios/reset
- /api/scenarios/load
"""

import os
from typing import Optional
from fastapi import Header, HTTPException, status

DEFAULT_ADMIN_KEY = "trust-admin-secret-dev"

def get_configured_admin_key() -> str:
    return os.getenv("ADMIN_API_KEY", DEFAULT_ADMIN_KEY)

def verify_admin_key(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """
    Validates that the caller has provided the valid administrative control secret
    either via 'X-Admin-Key' header or 'Authorization: Bearer <key>' header.
    Fails closed with HTTP 401 Unauthorized if missing or incorrect.
    """
    expected_key = get_configured_admin_key()

    bearer_token = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization[7:].strip()

    provided_key = x_admin_key or bearer_token

    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing administrative control key. Provide 'X-Admin-Key' or 'Authorization: Bearer <key>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if provided_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid administrative control key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return provided_key
