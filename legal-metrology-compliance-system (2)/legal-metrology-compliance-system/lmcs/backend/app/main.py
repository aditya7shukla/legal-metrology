import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import auth, products, scans, reports, dashboard

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("lmcs")

# Create tables if they don't exist. For real production schema evolution,
# use `alembic upgrade head` instead (see backend/alembic/).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Automated compliance-checking system for packaged commodity labels under the "
        "Legal Metrology (Packaged Commodities) Rules, 2011. Provides OCR-based declaration "
        "extraction, rule-based compliance evaluation, report generation, and an enforcement "
        "dashboard."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = str(round((time.time() - start) * 1000, 1))
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(products.router, prefix=settings.API_V1_PREFIX)
app.include_router(scans.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)

# Serve uploaded images / thumbnails directly (behind auth at the API layer;
# in production front this with signed URLs / a private bucket + CDN instead).
app.mount("/media", StaticFiles(directory=settings.UPLOAD_DIR), name="media")


@app.get("/api/health", tags=["System"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}
