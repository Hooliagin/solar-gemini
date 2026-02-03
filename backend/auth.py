from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import decode, PyJWTError
import os
from config import settings
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Supabase JWT secret for signature verification
# This is the project's JWT secret, NOT the anon key
SUPABASE_JWT_SECRET = settings.SUPABASE_JWT_SECRET

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Extracts the user_id (sub) from the Supabase JWT token.
    Verifies the token signature using SUPABASE_JWT_SECRET.
    """
    token = credentials.credentials
    try:
        # Verify signature with JWT secret
        if SUPABASE_JWT_SECRET:
            payload = decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
        else:
            # Fallback for development only - log warning
            logger.warning("SUPABASE_JWT_SECRET not set - JWT signature verification disabled!")
            payload = decode(token, options={"verify_signature": False})
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except PyJWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

