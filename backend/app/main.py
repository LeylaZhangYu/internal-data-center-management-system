from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.routers import administrators, auth, datacenters, devices, logs, network, overview, racks, visualization
from app.services.seed import seed_demo_data

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()] or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(overview.router, prefix=settings.api_prefix)
app.include_router(datacenters.router, prefix=settings.api_prefix)
app.include_router(racks.router, prefix=settings.api_prefix)
app.include_router(devices.router, prefix=settings.api_prefix)
app.include_router(administrators.router, prefix=settings.api_prefix)
app.include_router(network.router, prefix=settings.api_prefix)
app.include_router(logs.router, prefix=settings.api_prefix)
app.include_router(visualization.router, prefix=settings.api_prefix)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    if settings.seed_demo_data:
        db = SessionLocal()
        try:
            seed_demo_data(db)
        finally:
            db.close()


@app.get("/health")
def health():
    return {"status": "ok"}
