import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import projects, parts, generate, export, printers, sections, versions, imports, conversations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    os.makedirs(settings.temp_dir, exist_ok=True)
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="CAD 3D Generator",
    description="Web application for generating 3D printable models via natural language or CadQuery scripting",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(sections.router, prefix="/api", tags=["sections"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(parts.router, prefix="/api/parts", tags=["parts"])
app.include_router(parts.project_parts_router, prefix="/api", tags=["parts"])
app.include_router(versions.router, prefix="/api", tags=["versions"])
app.include_router(generate.router, prefix="/api", tags=["generate"])
app.include_router(export.router, prefix="/api", tags=["export"])
app.include_router(printers.router, prefix="/api/printers", tags=["printers"])
app.include_router(imports.router, prefix="/api", tags=["import"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Serve static frontend files in production
import os
static_dir = os.path.join(os.path.dirname(__file__), '..', 'static')
if os.path.exists(static_dir):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(static_dir, 'index.html'))
    
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
