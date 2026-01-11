"""
Authentication middleware for API
"""
from fastapi import Header, HTTPException, status
from typing import Optional
from server.database.task_manager import ClientManager
from server.config import config
import logging

logger = logging.getLogger(__name__)


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[str]:
    """
    Verify API key and return client ID
    """
    if not config.enable_auth:
        return None
    
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    client = ClientManager.get_client_by_api_key(x_api_key)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    if client['status'] != 'active':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client is not active"
        )
    
    return str(client['id'])
