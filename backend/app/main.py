from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api import regions

app = FastAPI(title="HarvestGuard AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(regions.router, prefix="/regions", tags=["regions"])

@app.get("/")
def health_check():
    return {"status": "ok", "project": "HarvestGuard AI"}
