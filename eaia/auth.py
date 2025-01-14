"""Authentication & authorization example."""

import os
from datetime import timedelta

import httpx
import jwt
from jwt.exceptions import InvalidTokenError
from langgraph_sdk import Auth

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]
ALGORITHM = "HS256"


AUTH_EXCEPTION = Auth.exceptions.HTTPException(
    status_code=401,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

auth = Auth()


@auth.authenticate
async def get_current_user(
    authorization: str | None,  # "Bearer <token>""
) -> Auth.types.MinimalUserDict:
    """Authenticate the user's JWT token."""
    assert authorization
    try:
        token = authorization.split(" ", 1)[1]
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            audience="authenticated",
            leeway=timedelta(seconds=60),
        )

        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": SUPABASE_SERVICE_KEY,
                },
            )
    except (IndexError, InvalidTokenError, ConnectionError) as e:
        raise AUTH_EXCEPTION from e
    if response.status_code != 200:
        raise AUTH_EXCEPTION

    user_data = response.json()
    return {
        "identity": user_data["id"],
        "full_name": user_data.get("user_metadata", {}).get("full_name"),
        "is_authenticated": True,
        "permissions": [payload["role"]],
    }


@auth.on
async def add_owner(
    ctx: Auth.types.AuthContext,
    value: dict,
):
    """Add the owner to the resource metadata and return filters."""
    if isinstance(ctx.user, Auth.types.StudioUser):
        return {}
    filters = {"owner": ctx.user.identity}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)
    return filters


@auth.on.store()
async def authorize_store(ctx: Auth.types.AuthContext, value: Auth.types.on):
    if isinstance(ctx.user, Auth.types.StudioUser):
        return {}
    namespace: tuple = value["namespace"]
    assert ctx.user.identity in namespace, "Not authorized"
