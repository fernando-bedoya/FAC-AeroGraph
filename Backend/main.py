"""
FastAPI Application Factory

Creates and configures the FastAPI application with routes and middleware.
No server startup logic here — use run.py for that.
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="SkyRoute Planner API",
        version="1.0.0",
        description="Graph-based flight route planning and dynamic simulation"
    )
    
    # Middleware para deshabilitar cache en desarrollo
    @app.middleware("http")
    async def add_no_cache_headers(request, call_next):
        response = await call_next(request)
        path = request.url.path
        # Deshabilitar cache para archivos JS, HTML y CSS
        if path.endswith(('.js', '.html', '.css')):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes FIRST - these have absolute priority
    app.include_router(router, prefix="/api")
    
    # Serve frontend static files - CRITICAL: Don't mount on "/" 
    frontend_path = Path(__file__).parent.parent / "Frontend"
    if frontend_path.exists():
        # Mount static asset directories
        app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")
        
        # Mount JS directory
        app.mount("/js", StaticFiles(directory=str(frontend_path / "js")), name="js")
        
        # Serve root index.html
        @app.get("/")
        async def serve_root():
            return FileResponse(frontend_path / "index.html")
        
        # Serve individual files and SPA fallback
        # This only handles GET requests, so it won't interfere with POST /api/* routes
        @app.get("/{path:path}")
        async def serve_frontend(path: str):
            # Serve the file if it exists
            file_path = frontend_path / path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            # SPA fallback: serve index.html for routes that don't exist
            return FileResponse(frontend_path / "index.html")
    
    return app


# Create app instance
app = create_app()
