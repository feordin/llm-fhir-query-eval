from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import test_cases
from src.utils.config import settings

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(test_cases.router, prefix="/api/test-cases", tags=["test-cases"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.api_version}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FHIR Query Evaluation API",
        "version": settings.api_version,
        "docs": "/docs"
    }
