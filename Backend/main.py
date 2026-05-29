"""
FastAPI Application Factory

Creates and configures the FastAPI application with routes and middleware.
No server startup logic here — use run.py for that.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="SkyRoute Planner API",
        version="1.0.0",
        description="Graph-based flight route planning and dynamic simulation"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router, prefix="/api")
    
    return app


# Create app instance
app = create_app()
