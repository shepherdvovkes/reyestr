"""
WebAuthn/FIDO2 authentication endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, List
import base64
import secrets
import logging
from server.database.webauthn_manager import WebAuthnManager
from server.database.connection import get_db_connection, return_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/webauthn", tags=["auth"])


class RegisterStartRequest(BaseModel):
    username: str
    displayName: str


class RegisterStartResponse(BaseModel):
    challenge: str
    rp: dict
    user: dict
    pubKeyCredParams: List[dict]
    authenticatorSelection: Optional[dict] = None
    timeout: int
    attestation: str


class RegisterCompleteRequest(BaseModel):
    id: str
    rawId: List[int]
    response: dict
    type: str


class LoginStartRequest(BaseModel):
    username: str


class LoginStartResponse(BaseModel):
    challenge: str
    allowCredentials: Optional[List[dict]] = None
    timeout: int
    userVerification: str
    rpId: str


class LoginCompleteRequest(BaseModel):
    id: str
    rawId: List[int]
    response: dict
    type: str


class AuthResponse(BaseModel):
    token: str
    user: dict


@router.post("/register/start", response_model=RegisterStartResponse)
async def register_start(request: RegisterStartRequest):
    """Start WebAuthn registration"""
    try:
        # Generate challenge
        challenge = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Store challenge temporarily (in production, use Redis or similar)
        # For now, we'll generate user ID
        user_id = base64.urlsafe_b64encode(request.username.encode()).decode('utf-8').rstrip('=')
        
        # Create credential creation options
        response = RegisterStartResponse(
            challenge=challenge,
            rp={
                "name": "Reyestr Admin",
                "id": "localhost"  # In production, use your domain
            },
            user={
                "id": user_id,
                "name": request.username,
                "displayName": request.displayName
            },
            pubKeyCredParams=[
                {"type": "public-key", "alg": -7},  # ES256
                {"type": "public-key", "alg": -257}  # RS256
            ],
            authenticatorSelection={
                "authenticatorAttachment": "cross-platform",
                "userVerification": "preferred"
            },
            timeout=60000,
            attestation="none"
        )
        
        # Store challenge for verification
        WebAuthnManager.store_challenge(request.username, challenge, "register")
        
        return response
    except Exception as e:
        logger.error(f"Error in register_start: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/register/complete", response_model=AuthResponse)
async def register_complete(request: RegisterCompleteRequest):
    """Complete WebAuthn registration"""
    try:
        # In production, verify the credential here
        # For now, we'll create a user and return a token
        
        # Extract username from credential ID (simplified)
        # In production, you'd verify the attestation
        
        # Create user and credential
        user_id = WebAuthnManager.create_user_with_credential(
            credential_id=request.id,
            public_key=request.response.get("attestationObject", []),
            username="user"  # Extract from challenge
        )
        
        # Generate JWT token (simplified - use proper JWT in production)
        token = secrets.token_urlsafe(32)
        
        # Store token (in production, use proper session management)
        WebAuthnManager.store_token(token, user_id)
        
        return AuthResponse(
            token=token,
            user={
                "id": user_id,
                "username": "user",
                "displayName": "User"
            }
        )
    except Exception as e:
        logger.error(f"Error in register_complete: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login/start", response_model=LoginStartResponse)
async def login_start(request: LoginStartRequest):
    """Start WebAuthn login"""
    try:
        # Get user's credentials
        credentials = WebAuthnManager.get_user_credentials(request.username)
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate challenge
        challenge = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Store challenge
        WebAuthnManager.store_challenge(request.username, challenge, "login")
        
        return LoginStartResponse(
            challenge=challenge,
            allowCredentials=[
                {
                    "id": cred["credential_id"],
                    "type": "public-key",
                    "transports": ["usb", "nfc", "ble", "internal"]
                }
                for cred in credentials
            ],
            timeout=60000,
            userVerification="preferred",
            rpId="localhost"  # In production, use your domain
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login_start: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/login/complete", response_model=AuthResponse)
async def login_complete(request: LoginCompleteRequest):
    """Complete WebAuthn login"""
    try:
        # In production, verify the assertion here
        # For now, we'll verify and return a token
        
        # Get user by credential ID
        user_id = WebAuthnManager.verify_credential(request.id)
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credential"
            )
        
        # Generate JWT token
        token = secrets.token_urlsafe(32)
        WebAuthnManager.store_token(token, user_id)
        
        # Get user info
        user = WebAuthnManager.get_user(user_id)
        
        return AuthResponse(
            token=token,
            user={
                "id": user_id,
                "username": user.get("username", ""),
                "displayName": user.get("display_name", "")
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login_complete: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
