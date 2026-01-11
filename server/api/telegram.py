"""
Telegram notification service
"""
import logging
import requests
from typing import Optional
from server.config import config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send notifications via Telegram"""
    
    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or getattr(config, 'telegram_bot_token', None)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
    
    def send_message(self, chat_id: str, message: str) -> bool:
        """Send message to Telegram chat"""
        if not self.base_url:
            logger.warning("Telegram bot token not configured")
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                },
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def send_critical_error(
        self,
        chat_id: str,
        error_message: str,
        task_id: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> bool:
        """Send critical error notification"""
        message = f"<b>Critical Error</b>\n\n"
        message += f"Error: {error_message}\n"
        if task_id:
            message += f"Task ID: {task_id}\n"
        if client_id:
            message += f"Client ID: {client_id}\n"
        
        return self.send_message(chat_id, message)


# Global instance
telegram_notifier = TelegramNotifier()
