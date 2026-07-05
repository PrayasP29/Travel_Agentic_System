from database.crud import get_user_by_email
from database.models import User
from sqlalchemy.ext.asyncio import AsyncSession


async def get_google_user_info(access_token: str) -> dict:
    # TODO: GET https://www.googleapis.com/oauth2/v2/userinfo
    # Headers: Authorization: Bearer {access_token}
    # Returns: {id, email, name, picture}
    raise NotImplementedError(
        "Wire to /auth/google/callback when frontend exists"
    )


async def get_github_user_info(access_token: str) -> dict:
    # TODO: GET https://api.github.com/user
    # Headers: Authorization: Bearer {access_token}
    # Returns: {id, email, login, name}
    raise NotImplementedError(
        "Wire to /auth/github/callback when frontend exists"
    )


async def create_or_get_oauth_user(
    db: AsyncSession,
    provider: str,
    oauth_id: str,
    email: str,
    name: str,
) -> User:
    # 1. Check if user with this oauth_id+provider exists
    # 2. If yes: return existing user
    # 3. If no: create new user with unusable password hash
    #    hashed_password = "oauth::{provider}::{oauth_id}"
    # This is called by /auth/google/callback and
    # /auth/github/callback when those routes are added
    pass
