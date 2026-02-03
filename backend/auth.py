from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import decode, PyJWTError, PyJWKClient
import os
from config import settings
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Supabase JWT secret for HS256
SUPABASE_JWT_SECRET = settings.SUPABASE_JWT_SECRET

# JWKS Client for ES256 (Global to reuse if possible, though caching depends on library)
# JWKS Client for ES256 (Global to reuse if possible, though caching depends on library)
jwks_client = None
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    # Construct JWKS URL: https://project.supabase.co/auth/v1/jwks
    jwks_url = f"{settings.SUPABASE_URL}/auth/v1/jwks"
    try:
        # Supabase API Gateway requires 'apikey' header even for public endpoints in some configs
        jwks_client = PyJWKClient(jwks_url, headers={"apikey": settings.SUPABASE_KEY})
    except Exception as e:
        logger.warning(f"Failed to initialize PyJWKClient: {e}")
else:
    if not settings.SUPABASE_URL:
        logger.warning("AUTH: SUPABASE_URL not set. JWKS support disabled.")
    if not settings.SUPABASE_KEY:
        logger.warning("AUTH: SUPABASE_KEY not set. JWKS support disabled.")

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Extracts the user_id (sub) from the Supabase JWT token.
    Supports both HS256 (Secret) and ES256 (JWKS).
    """
    token = credentials.credentials
    try:
        # 1. Peek at the header to determine algorithm
        import jwt
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get('alg')

        payload = None

        if alg == 'HS256':
            # Verify with Symmetric Secret
            if SUPABASE_JWT_SECRET:
                payload = decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
            else:
                logger.warning("HS256 Token received but SUPABASE_JWT_SECRET is not set!")
                raise Exception("Missing JWT Secret for HS256")
        
        elif alg == 'ES256' or alg == 'RS256':
            # Verify with JWKS (Asymmetric)
            if not jwks_client:
                logger.error(f"{alg} Token received but SUPABASE_URL is not set (cannot fetch JWKS).")
                raise Exception("Missing SUPABASE_URL for JWKS")
            
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = decode(token, signing_key.key, algorithms=[alg], audience="authenticated")
            
        else:
            # Fallback (Dev/Unknown)
            logger.warning(f"Unknown JWT Algorithm: {alg}. Attempting unsafe decode if dev.")
            # For strict production, we should probably fail here. 
            # But preserving old behavior (warning) if we can't verify signature.
            # Actually, standard is to FAIL.
            if not SUPABASE_JWT_SECRET and not jwks_client:
                 # Only if NO config is present, maybe allow? No, that's unsafe.
                 pass
            raise Exception(f"Unsupported JWT Algorithm: {alg}")

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token valid but missing 'sub'",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id

    except Exception as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

