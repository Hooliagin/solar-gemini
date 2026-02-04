from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import decode, PyJWTError
import os
from config import settings
import logging
import json
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Supabase JWT secret for HS256
SUPABASE_JWT_SECRET = settings.SUPABASE_JWT_SECRET

# JWKS Cache (fetched once at startup if possible)
_jwks_cache = None
_jwks_url = None

def _fetch_jwks():
    """Fetch JWKS from Supabase with proper apikey header."""
    global _jwks_cache, _jwks_url
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning("Cannot fetch JWKS: SUPABASE_URL or SUPABASE_KEY not set")
        return None
    
    base_url = settings.SUPABASE_URL.rstrip('/')
    _jwks_url = f"{base_url}/auth/v1/.well-known/jwks.json"
    
    try:
        req = urllib.request.Request(_jwks_url)
        req.add_header('apikey', settings.SUPABASE_KEY)
        req.add_header('Authorization', f'Bearer {settings.SUPABASE_KEY}')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            _jwks_cache = data
            logger.info(f"Successfully fetched JWKS from {_jwks_url}")
            return data
    except urllib.error.HTTPError as e:
        logger.error(f"Failed to fetch JWKS: HTTP {e.code} - {e.reason}")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        return None

def _get_signing_key(token: str):
    """Get the signing key for a JWT from cached JWKS."""
    global _jwks_cache
    
    import jwt
    from jwt import PyJWK
    
    # Fetch JWKS if not cached
    if _jwks_cache is None:
        _fetch_jwks()
    
    if _jwks_cache is None:
        raise Exception("JWKS not available")
    
    # Get the kid from the token header
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get('kid')
    
    if not kid:
        raise Exception("Token missing 'kid' header")
    
    # Find the matching key
    for key_data in _jwks_cache.get('keys', []):
        if key_data.get('kid') == kid:
            return PyJWK.from_dict(key_data).key
    
    # Key not found - maybe JWKS was rotated, try refetching
    logger.info(f"Key {kid} not found in cache, refetching JWKS...")
    _fetch_jwks()
    
    if _jwks_cache:
        for key_data in _jwks_cache.get('keys', []):
            if key_data.get('kid') == kid:
                return PyJWK.from_dict(key_data).key
    
    raise Exception(f"Signing key with kid '{kid}' not found in JWKS")

# Pre-fetch JWKS at startup
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    _fetch_jwks()

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
            # Verify with JWKS (Asymmetric) using our manual fetcher
            signing_key = _get_signing_key(token)
            payload = decode(token, signing_key, algorithms=[alg], audience="authenticated")
            
        else:
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
