"""Minimal role-based auth for the exercise.

Real auth is Keycloak/OIDC; here the caller's role is passed in an ``X-Role``
header so you can focus on the business logic. Use ``require_role(...)`` as a
FastAPI dependency to gate an endpoint.

Roles: analyst, manager, admin, customer, system.
"""

from fastapi import Header, HTTPException


def require_role(*allowed: str):
    def _dep(x_role: str = Header(default="")) -> str:
        if x_role not in allowed:
            raise HTTPException(
                status_code=403, detail=f"role '{x_role}' not permitted"
            )
        return x_role

    return _dep
