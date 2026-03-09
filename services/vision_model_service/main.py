"""
Vision Model Service - Main application entry point.
Processes medical images with OpenCV and routes to llava via ollama_router_service.
Port: 8053
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router

app = FastAPI(
    title="Vision Model Service",
    description="Medical image analysis using LLaVA with OpenCV preprocessing (CLAHE, denoising). Returns structured clinical findings.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "vision_model_service", "port": 8053}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8053, reload=True)
