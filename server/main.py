"""
Main FastAPI application for download server
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from server.config import config
from server.api.routes import router
from server.api.webauthn import router as webauthn_router
from server.api.users import router as users_router
from server.database.connection import get_connection_pool, close_connection_pool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info("Starting download server...")
    try:
        # Initialize database connection pool
        get_connection_pool()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down download server...")
    close_connection_pool()
    logger.info("Database connection pool closed")


# Create FastAPI app
app = FastAPI(
    title=config.api_title,
    version=config.api_version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)
app.include_router(webauthn_router)
app.include_router(users_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Reyestr Download Server",
        "version": config.api_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        pool = get_connection_pool()
        conn = pool.getconn()
        conn.close()
        pool.putconn(conn)
        
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=True
    )
