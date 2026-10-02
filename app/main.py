from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.database import Base, engine
from app.core.exceptions import DomainError
from app.core.logging import setup_logging
from app.models import models  # noqa: F401  (registers tables on Base.metadata)
from app.routers import auth, bookings, centres, payments

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fine for this assignment; use Alembic migrations in production.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="EVE Diagnostics API",
    description="Diagnostic test bookings with simulated payments.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


app.include_router(auth.router)
app.include_router(centres.centres_router)
app.include_router(centres.tests_router)
app.include_router(bookings.router)
app.include_router(payments.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
