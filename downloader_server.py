"""
Download Server - Centralized task management server for distributed downloads
Run this on the gate server to coordinate multiple download clients
"""
import uvicorn
import logging
import sys
from pathlib import Path

# Add server module to path
sys.path.insert(0, str(Path(__file__).parent))

from server.main import app
from server.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for download server"""
    logger.info("=" * 60)
    logger.info("Reyestr Download Server")
    logger.info("=" * 60)
    logger.info(f"API Host: {config.api_host}")
    logger.info(f"API Port: {config.api_port}")
    logger.info(f"Database: {config.db_host}:{config.db_port}/{config.db_name}")
    logger.info(f"Authentication: {'Enabled' if config.enable_auth else 'Disabled'}")
    logger.info("=" * 60)
    
    try:
        uvicorn.run(
            app,
            host=config.api_host,
            port=config.api_port,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
