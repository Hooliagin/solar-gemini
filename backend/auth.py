from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import decode, PyJWKClient, PyJWTError
import os
from config import settings

security = HTTPBearer()

# Supabase Project parameters
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_JWT_SECRET = settings.SUPABASE_KEY # In some setups, this might be the anon key, but usually verifying requires the project JWT secret.
# However, verification via Supabase usually involves checking against the project's JWT secret OR using the JWKS endpoint.
# With Supabase, the "anon" key is public, but the access token after login is signed with the project secret.

# NOTE: For simplicity in this project, we will decode the JWT without signature verification (trusting the gateway/client for now) 
# OR use the SUPABASE_JWT_SECRET if available. A proper production setup should use the project's JWT secret to verify signature.
# Given we are backend behind possible gateways, checking the 'sub' (user_id) is the primary goal.

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Extracts the user_id (sub) from the Supabase JWT token.
    Verifies the token is present.
    """
    token = credentials.credentials
    try:
        # Decode WITH verification.
        # We use the HMAC algorithm (HS256) which Supabase uses for signed tokens.
        payload = decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
