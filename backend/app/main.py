from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import kits, manuals, scrape


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="GunplaDB API",
    description="Database of all Gunpla model kits with instruction manuals",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kits.router, prefix="/api")
app.include_router(manuals.router, prefix="/api")
app.include_router(scrape.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
