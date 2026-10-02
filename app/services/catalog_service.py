from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.models.models import Centre, CentreTest, Test
from app.schemas.catalog import (
    CentreCreate,
    CentreOut,
    CentreTestOut,
    TestCreate,
)


def centre_to_out(centre: Centre) -> CentreOut:
    return CentreOut(
        id=centre.id,
        name=centre.name,
        location=centre.location,
        tests=[
            CentreTestOut(test_id=o.test_id, name=o.test.name, price=o.price)
            for o in centre.offerings
        ],
    )


def list_centres(
    db: Session, skip: int, limit: int, location: str | None
) -> tuple[list[Centre], int]:
    stmt = select(Centre)
    if location:
        stmt = stmt.where(Centre.location.ilike(f"%{location}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(selectinload(Centre.offerings).joinedload(CentreTest.test))
        .order_by(Centre.id)
        .offset(skip)
        .limit(limit)
    ).all()
    return list(rows), total


def get_centre(db: Session, centre_id: int) -> Centre:
    centre = db.scalar(
        select(Centre)
        .where(Centre.id == centre_id)
        .options(selectinload(Centre.offerings).joinedload(CentreTest.test))
    )
    if centre is None:
        raise NotFoundError("Centre not found")
    return centre


def create_centre(db: Session, data: CentreCreate) -> Centre:
    centre = Centre(name=data.name, location=data.location)
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


def create_test(db: Session, data: TestCreate) -> Test:
    if db.scalar(select(Test.id).where(Test.name == data.name)):
        raise ConflictError("A test with this name already exists")
    test = Test(name=data.name, description=data.description)
    db.add(test)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("A test with this name already exists")
    db.refresh(test)
    return test


def list_tests(db: Session, skip: int, limit: int) -> tuple[list[Test], int]:
    total = db.scalar(select(func.count()).select_from(Test)) or 0
    rows = db.scalars(select(Test).order_by(Test.id).offset(skip).limit(limit)).all()
    return list(rows), total


def add_test_to_centre(
    db: Session, centre_id: int, test_id: int, price: Decimal
) -> None:
    if db.get(Centre, centre_id) is None:
        raise NotFoundError("Centre not found")
    if db.get(Test, test_id) is None:
        raise NotFoundError("Test not found")
    exists = db.scalar(
        select(CentreTest.id).where(
            CentreTest.centre_id == centre_id, CentreTest.test_id == test_id
        )
    )
    if exists:
        raise ConflictError("This test is already offered at this centre")
    db.add(CentreTest(centre_id=centre_id, test_id=test_id, price=price))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("This test is already offered at this centre")
