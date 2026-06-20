import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify Firebase ID token and return decoded user payload."""
    try:
        decoded_token = auth.verify_id_token(credentials.credentials)
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
