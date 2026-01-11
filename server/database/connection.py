"""
Database connection management
"""
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import logging
from typing import Optional
from server.config import config

logger = logging.getLogger(__name__)

# Connection pool
_connection_pool: Optional[pool.ThreadedConnectionPool] = None


def get_connection_pool() -> pool.ThreadedConnectionPool:
    """Get or create database connection pool"""
    global _connection_pool
    
    if _connection_pool is None:
        try:
            _connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=config.db_pool_minconn,
                maxconn=config.db_pool_maxconn,
                host=config.db_host,
                port=config.db_port,
                database=config.db_name,
                user=config.db_user,
                password=config.db_password,
                cursor_factory=RealDictCursor
            )
            logger.info(f"Database connection pool created: min={config.db_pool_minconn}, max={config.db_pool_maxconn}")
        except Exception as e:
            logger.error(f"Error creating connection pool: {e}")
            raise
    
    return _connection_pool


def get_db_connection():
    """Get a database connection from the pool"""
    pool = get_connection_pool()
    return pool.getconn()


def return_db_connection(conn):
    """Return a connection to the pool"""
    pool = get_connection_pool()
    pool.putconn(conn)


def close_connection_pool():
    """Close the connection pool"""
    global _connection_pool
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("Database connection pool closed")
