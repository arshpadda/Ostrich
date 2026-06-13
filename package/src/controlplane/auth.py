import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verify Firebase ID token and return decoded user payload."""
    try:
        decoded_token = auth.verify_id_token(credentials.credentials)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def init_firebase():
    """Initialize Firebase Admin SDK using Application Default Credentials."""
    if not firebase_admin._apps:
        # In Cloud Run, this will automatically use the service account credentials.
        # Locally, it will use the credentials from `gcloud auth application-default login`.
        firebase_admin.initialize_app()
