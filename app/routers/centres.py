from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import require_admin
from app.schemas.catalog import (
    CentreCreate,
    CentreOut,
    CentreTestCreate,
    TestCreate,
    TestOut,
)
from app.schemas.common import Page
from app.services import catalog_service as svc

centres_router = APIRouter(prefix="/centres", tags=["centres"])
tests_router = APIRouter(prefix="/tests", tags=["tests"])


# ---- centres ---------------------------------------------------------------
@centres_router.get("/", response_model=Page[CentreOut])
def list_centres(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    location: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
):
    centres, total = svc.list_centres(db, skip, limit, location)
    return Page[CentreOut](
        items=[svc.centre_to_out(c) for c in centres],
        total=total,
        skip=skip,
        limit=limit,
    )


@centres_router.get("/{centre_id}", response_model=CentreOut)
def get_centre(centre_id: int, db: Session = Depends(get_db)):
    return svc.centre_to_out(svc.get_centre(db, centre_id))


@centres_router.post(
    "/", response_model=CentreOut, status_code=201, dependencies=[Depends(require_admin)]
)
def create_centre(payload: CentreCreate, db: Session = Depends(get_db)):
    centre = svc.create_centre(db, payload)
    return CentreOut(id=centre.id, name=centre.name, location=centre.location, tests=[])


@centres_router.post(
    "/{centre_id}/tests",
    response_model=CentreOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def add_test_to_centre(
    centre_id: int, payload: CentreTestCreate, db: Session = Depends(get_db)
):
    svc.add_test_to_centre(db, centre_id, payload.test_id, payload.price)
    return svc.centre_to_out(svc.get_centre(db, centre_id))


# ---- tests catalogue -------------------------------------------------------
@tests_router.get("/", response_model=Page[TestOut])
def list_tests(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    tests, total = svc.list_tests(db, skip, limit)
    return Page[TestOut](
        items=[TestOut.model_validate(t) for t in tests],
        total=total,
        skip=skip,
        limit=limit,
    )


@tests_router.post(
    "/", response_model=TestOut, status_code=201, dependencies=[Depends(require_admin)]
)
def create_test(payload: TestCreate, db: Session = Depends(get_db)):
    return svc.create_test(db, payload)
