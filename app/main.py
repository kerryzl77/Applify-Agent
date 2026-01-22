"""FastAPI application entry point."""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.config import get_settings
from app.routers import auth_router, content_router, resume_router, gmail_router
from app.dependencies import get_db, get_redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Determine paths
BASE_DIR = Path(__file__).resolve().parent.parent
CLIENT_DIST = BASE_DIR / "client" / "dist"

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI-powered job application assistant",
    version="2.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS configuration
allowed_origins = settings.allowed_origins
if allowed_origins != "*":
    origins = [origin.strip() for origin in allowed_origins.split(",")]
else:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(content_router, prefix="/api/content", tags=["Content Generation"])
app.include_router(resume_router, prefix="/api/resume", tags=["Resume"])
app.include_router(gmail_router, prefix="/api/gmail", tags=["Gmail"])

# Legacy endpoint aliases for backward compatibility
# These redirect to the new endpoints
from fastapi import Request
from fastapi.responses import RedirectResponse

@app.api_route("/api/login", methods=["POST"], include_in_schema=False)
async def legacy_login(request: Request):
    """Legacy login endpoint - redirects to /api/auth/login."""
    return RedirectResponse(url="/api/auth/login", status_code=307)

@app.api_route("/api/register", methods=["POST"], include_in_schema=False)
async def legacy_register(request: Request):
    """Legacy register endpoint - redirects to /api/auth/register."""
    return RedirectResponse(url="/api/auth/register", status_code=307)

@app.api_route("/api/logout", methods=["POST"], include_in_schema=False)
async def legacy_logout(request: Request):
    """Legacy logout endpoint - redirects to /api/auth/logout."""
    return RedirectResponse(url="/api/auth/logout", status_code=307)

@app.api_route("/api/auth/check", methods=["GET"], include_in_schema=False)
async def legacy_auth_check(request: Request):
    """Legacy auth check - handled by auth router."""
    # This is already handled by the auth router, just ensuring route exists
    pass

@app.api_route("/api/candidate-data", methods=["GET", "POST"], include_in_schema=False)
async def legacy_candidate_data(request: Request):
    """Legacy candidate data endpoint."""
    method = request.method
    if method == "GET":
        return RedirectResponse(url="/api/content/candidate-data", status_code=307)
    return RedirectResponse(url="/api/content/candidate-data", status_code=307)

@app.api_route("/api/update-candidate-data", methods=["POST"], include_in_schema=False)
async def legacy_update_candidate_data(request: Request):
    """Legacy update candidate data endpoint."""
    return RedirectResponse(url="/api/content/candidate-data", status_code=307)

@app.api_route("/api/generate", methods=["POST"], include_in_schema=False)
async def legacy_generate(request: Request):
    """Legacy generate endpoint."""
    return RedirectResponse(url="/api/content/generate", status_code=307)

@app.api_route("/api/upload-resume", methods=["POST"], include_in_schema=False)
async def legacy_upload_resume(request: Request):
    """Legacy resume upload endpoint."""
    return RedirectResponse(url="/api/resume/upload", status_code=307)

@app.api_route("/api/refine-resume", methods=["POST"], include_in_schema=False)
async def legacy_refine_resume(request: Request):
    """Legacy resume refine endpoint."""
    return RedirectResponse(url="/api/resume/refine", status_code=307)

@app.api_route("/api/resume-progress", methods=["GET"], include_in_schema=False)
async def legacy_resume_progress(request: Request):
    """Legacy resume progress endpoint."""
    return RedirectResponse(url="/api/resume/progress", status_code=307)

@app.api_route("/api/resume-refinement-progress/{task_id}", methods=["GET"], include_in_schema=False)
async def legacy_refinement_progress(task_id: str):
    """Legacy refinement progress endpoint."""
    return RedirectResponse(url=f"/api/resume/refinement-progress/{task_id}", status_code=307)

@app.api_route("/api/download/{file_path:path}", methods=["GET"], include_in_schema=False)
async def legacy_download(file_path: str):
    """Legacy download endpoint."""
    return RedirectResponse(url=f"/api/content/download/{file_path}", status_code=307)

@app.api_route("/api/convert-to-pdf/{file_path:path}", methods=["GET"], include_in_schema=False)
async def legacy_convert_pdf(file_path: str):
    """Legacy PDF conversion endpoint."""
    return RedirectResponse(url=f"/api/content/convert-to-pdf/{file_path}", status_code=307)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for container monitoring."""
    try:
        db = get_db()
        redis = get_redis()
        
        # Check database connection
        try:
            conn = db._get_connection()
            if conn:
                db._return_connection(conn)
                db_healthy = True
            else:
                db_healthy = False
        except Exception:
            db_healthy = False
        
        # Check Redis connection
        redis_healthy = redis.is_available()
        
        status_value = "healthy" if db_healthy and redis_healthy else "unhealthy"
        
        return JSONResponse(
            content={
                "status": status_value,
                "database": "up" if db_healthy else "down",
                "redis": "up" if redis_healthy else "down",
                "timestamp": datetime.now().isoformat(),
            },
            status_code=200 if status_value == "healthy" else 503,
        )
        
    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            },
            status_code=503,
        )


# Serve static files from client/dist
if CLIENT_DIST.exists():
    # Mount assets directory
    assets_dir = CLIENT_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    # Serve other static files
    @app.get("/vite.svg")
    async def serve_vite_svg():
        svg_path = CLIENT_DIST / "vite.svg"
        if svg_path.exists():
            return FileResponse(str(svg_path))
        return JSONResponse({"error": "Not found"}, status_code=404)


# Catch-all route to serve React app (must be last)
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Serve React app for all non-API routes."""
    # Skip API routes
    if full_path.startswith("api/"):
        return JSONResponse({"error": "Not found"}, status_code=404)
    
    # Try to serve static file first
    file_path = CLIENT_DIST / full_path
    if full_path and file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    
    # Serve index.html for SPA routing
    index_path = CLIENT_DIST / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    else:
        logger.error(f"index.html not found at {index_path}")
        return JSONResponse(
            {"error": "Frontend not found", "client_dist": str(CLIENT_DIST)},
            status_code=500,
        )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info(f"Starting {settings.app_name} in {settings.environment} mode")
    logger.info(f"Client dist path: {CLIENT_DIST}")
    
    # Initialize database
    try:
        db = get_db()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Initialize Redis
    redis = get_redis()
    if redis.is_available():
        logger.info("Redis available for caching")
    else:
        logger.warning("Redis unavailable, caching disabled")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down application")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.debug,
    )
