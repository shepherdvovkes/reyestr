"""
WebAuthn credential and user management
"""
import uuid
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from server.database.connection import get_db_connection, return_db_connection

logger = logging.getLogger(__name__)

# In-memory storage for challenges (use Redis in production)
_challenges: Dict[str, Dict] = {}
_tokens: Dict[str, str] = {}


class WebAuthnManager:
    """Manages WebAuthn credentials and users"""
    
    @staticmethod
    def store_challenge(username: str, challenge: str, type: str):
        """Store challenge temporarily"""
        key = f"{username}:{type}"
        _challenges[key] = {
            "challenge": challenge,
            "username": username,
            "type": type,
            "created_at": datetime.utcnow()
        }
        # Clean up old challenges
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        _challenges.clear()  # Simplified - in production, use TTL
    
    @staticmethod
    def get_challenge(username: str, type: str) -> Optional[str]:
        """Get stored challenge"""
        key = f"{username}:{type}"
        challenge_data = _challenges.get(key)
        if challenge_data:
            return challenge_data["challenge"]
        return None
    
    @staticmethod
    def create_user_with_credential(credential_id: str, public_key: List[int], username: str) -> str:
        """Create user and store credential"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Check if user exists
            cur.execute("""
                SELECT id FROM users WHERE username = %s
            """, (username,))
            user = cur.fetchone()
            
            if user:
                user_id = str(user['id'])
            else:
                # Create new user
                user_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO users (id, username, display_name, created_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                """, (user_id, username, username))
            
            # Store credential
            credential_uuid = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO webauthn_credentials (
                    id, user_id, credential_id, public_key, created_at
                )
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (credential_id) DO NOTHING
            """, (credential_uuid, user_id, credential_id, json.dumps(public_key)))
            
            conn.commit()
            cur.close()
            return user_id
            
        except Exception as e:
            logger.error(f"Error creating user with credential: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def get_user_credentials(username: str) -> List[Dict]:
        """Get all credentials for a user"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT wc.credential_id, wc.public_key
                FROM webauthn_credentials wc
                JOIN users u ON u.id = wc.user_id
                WHERE u.username = %s
            """, (username,))
            
            credentials = [
                {
                    "credential_id": row['credential_id'],
                    "public_key": row['public_key']
                }
                for row in cur.fetchall()
            ]
            
            cur.close()
            return credentials
            
        except Exception as e:
            logger.error(f"Error getting user credentials: {e}")
            return []
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def verify_credential(credential_id: str) -> Optional[str]:
        """Verify credential and return user ID"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT user_id FROM webauthn_credentials
                WHERE credential_id = %s
            """, (credential_id,))
            
            result = cur.fetchone()
            cur.close()
            
            if result:
                return str(result['user_id'])
            return None
            
        except Exception as e:
            logger.error(f"Error verifying credential: {e}")
            return None
        finally:
            if conn:
                return_db_connection(conn)
    
    @staticmethod
    def store_token(token: str, user_id: str):
        """Store authentication token"""
        _tokens[token] = user_id
    
    @staticmethod
    def get_user_by_token(token: str) -> Optional[str]:
        """Get user ID by token"""
        return _tokens.get(token)
    
    @staticmethod
    def get_user(user_id: str) -> Dict:
        """Get user information"""
        conn = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, username, display_name, email, telegram_chat_id
                FROM users
                WHERE id = %s
            """, (user_id,))
            
            user = cur.fetchone()
            cur.close()
            
            if user:
                return dict(user)
            return {}
            
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return {}
        finally:
            if conn:
                return_db_connection(conn)
