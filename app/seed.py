"""Seed demo data: an admin user plus a few centres and tests.

Run:  python -m app.seed
"""
from decimal import Decimal

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.models import Centre, CentreTest, Test, User

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@12345"

TESTS = ["Complete Blood Count", "Lipid Profile", "Chest X-Ray"]
CENTRES = {
    "EVE Diagnostics - Indiranagar": ("Bengaluru", [1200, 800, 600]),
    "EVE Diagnostics - Tumakuru": ("Tumakuru", [1000, 700, 500]),
}


def run() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if not db.scalar(select(User.id).where(User.email == ADMIN_EMAIL)):
            db.add(
                User(
                    email=ADMIN_EMAIL,
                    hashed_password=hash_password(ADMIN_PASSWORD),
                    full_name="Admin",
                    is_admin=True,
                )
            )

        tests = {}
        for name in TESTS:
            t = db.scalar(select(Test).where(Test.name == name))
            if t is None:
                t = Test(name=name)
                db.add(t)
            tests[name] = t
        db.flush()

        for centre_name, (location, prices) in CENTRES.items():
            c = db.scalar(select(Centre).where(Centre.name == centre_name))
            if c is None:
                c = Centre(name=centre_name, location=location)
                db.add(c)
                db.flush()
                for test_name, price in zip(TESTS, prices):
                    db.add(
                        CentreTest(
                            centre_id=c.id,
                            test_id=tests[test_name].id,
                            price=Decimal(price),
                        )
                    )
        db.commit()
    print(f"Seeded. Admin login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    run()
