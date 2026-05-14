"""
Permissions.py to get the role permissions
"""

from __future__ import annotations

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "EMPLOYEE": [
        "dashboard:view",
        "seat:book_self",
        "booking:view_own",
        "booking:cancel_own",
    ],

    "OFFICE_ADMIN": [
        "dashboard:view",
        "seat:book_self",
        "booking:view_own",
        "booking:cancel_own",
        "seat:block",
        "booking:view_all",
        "floor:view",
        "admin_dashboard:view",
    ],

    "TENANT_ADMIN": [
        "dashboard:view",
        "seat:book_self",
        "booking:view_own",
        "booking:cancel_own",
        "seat:block",
        "booking:view_all",
        "floor:view",
        "floor:manage",
        "layout:upload",
        "layout:publish",
        "seat:create",
        "seat:update",
        "seat:delete",
        "user:view",
        "user:manage",
        "admin_dashboard:view",
    ],

    "SUPPORT_ADMIN": [
        "dashboard:view",
        "booking:view_all",
        "user:view",
        "tenant:view",
        "support:manage",
        "admin_dashboard:view",
    ],
}


def resolve_permissions(role: str | None) -> list[str]:
    if not role:
        return []

    normalized_role = role.strip().upper()

    permissions = ROLE_PERMISSIONS.get(normalized_role, [])

    return sorted(set(permissions))