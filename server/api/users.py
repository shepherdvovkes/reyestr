"""
User management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status, Header
from pydantic import BaseModel
from typing import Optional
import logging
from server.database.webauthn_manager import WebAuthnManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    email: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    created_at: str
    updated_at: str


class UpdateUserRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    telegram_chat_id: Optional[str] = None


def get_current_user_id(
    authorization: Optional[str] = Header(None)
) -> Optional[str]:
    """Get current user ID from token"""
    if not authorization:
        return None
    
    # Extract token from "Bearer <token>" format
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    
    return WebAuthnManager.get_user_by_token(token)


@router.get("/me", response_model=UserResponse)
async def get_profile(user_id: Optional[str] = Depends(get_current_user_id)):
    """Get current user profile"""
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    user = WebAuthnManager.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.get("id", ""),
        username=user.get("username", ""),
        display_name=user.get("display_name", ""),
        email=user.get("email"),
        telegram_chat_id=user.get("telegram_chat_id"),
        created_at="",
        updated_at=""
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateUserRequest,
    user_id: Optional[str] = Depends(get_current_user_id)
):
    """Update current user profile"""
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    from server.database.connection import get_db_connection, return_db_connection
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build update query
        updates = []
        values = []
        
        if request.display_name is not None:
            updates.append("display_name = %s")
            values.append(request.display_name)
        
        if request.email is not None:
            updates.append("email = %s")
            values.append(request.email)
        
        if request.telegram_chat_id is not None:
            updates.append("telegram_chat_id = %s")
            values.append(request.telegram_chat_id)
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(user_id)
        
        cur.execute(f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, username, display_name, email, telegram_chat_id, created_at, updated_at
        """, values)
        
        user = cur.fetchone()
        conn.commit()
        cur.close()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            id=str(user['id']),
            username=user['username'],
            display_name=user['display_name'],
            email=user.get('email'),
            telegram_chat_id=user.get('telegram_chat_id'),
            created_at=user['created_at'].isoformat() if user.get('created_at') else "",
            updated_at=user['updated_at'].isoformat() if user.get('updated_at') else ""
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        if conn:
            return_db_connection(conn)
