from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import agent as agent_router
from routers import fined_tuned_models as fined_tuned_models_router
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="GCP Agent and fine tuned Model API",
    description="Cloud Run FastAPI for GCP Agent and fine-tuned model conversations",
    version="1.0.0",
    docs_url='/docs',
    openapi_url='/openapi.json',
    redoc_url='/redoc'
)

# Enable CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "GCP Agent and fine tuned Model API",
        "message": "Service is running successfully"
    }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "GCP Agent and fine tuned Model API",
        "version": "1.0.0",
        "description": "Conversation system using GCP Agents and fine-tuned models",
        "endpoints": {
            "invoke-agent": "/invoke-agent (POST)",
            "invoke-model": "/invoke-model (POST)",
            "health": "/health (GET)",
            "docs": "/docs (GET)",
            "openapi": "/openapi.json (GET)"
        }
    }


# Include agent router
app.include_router(agent_router.router)
app.include_router(fined_tuned_models_router.router)

# Optional: Run the app locally for development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 