import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

security = HTTPBearer()


import asyncio


def _verify_id_token(token: str) -> dict:
    return auth.verify_id_token(token)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify Firebase ID token and return decoded user payload."""
    try:
        # Performance Note (Bolt ⚡):
        # auth.verify_id_token is a synchronous blocking call.
        # Calling it directly in an async dependency blocks the FastAPI event loop.
        # Offloading it via asyncio.to_thread prevents freezing concurrent requests.
        # Making the dependency itself `async def` avoids FastAPI's threadpool overhead
        # and ensures `user_id_context.set` actually propagates to the main async context.
        decoded_token = await asyncio.to_thread(_verify_id_token, credentials.credentials)
        from .logging_config import user_id_context

        user_id_context.set(decoded_token.get("uid", ""))
        return decoded_token
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def init_firebase():
    """Initialize Firebase Admin SDK using Application Default Credentials."""
    if not firebase_admin._apps:
        # In Cloud Run, this will automatically use the service account credentials.
        # Locally, it will use the credentials from `gcloud auth application-default login`.
        import os

        project_id = os.getenv("PROJECT_ID", "ostr-499118")
        firebase_admin.initialize_app(options={"projectId": project_id})
