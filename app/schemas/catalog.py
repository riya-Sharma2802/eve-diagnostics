from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TestCreate(BaseModel):
    __test__ = False  # not a pytest class

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)


class TestOut(BaseModel):
    __test__ = False

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class CentreCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=150)
    location: str = Field(min_length=1, max_length=255)


class CentreTestCreate(BaseModel):
    test_id: int
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class CentreTestOut(BaseModel):
    test_id: int
    name: str
    price: Decimal


class CentreOut(BaseModel):
    id: int
    name: str
    location: str
    tests: list[CentreTestOut]
