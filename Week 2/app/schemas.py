from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    orderNumber: int
    orderDate: date
    requiredDate: date
    shippedDate: date | None = None
    status: str
    comments: str | None = None


class PaymentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customerNumber: int
    checkNumber: str
    paymentDate: date
    amount: Decimal


class CustomerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customerName: str
    contactLastName: str
    contactFirstName: str
    phone: str
    addressLine1: str
    addressLine2: str | None = None
    city: str
    state: str | None = None
    postalCode: str | None = None
    country: str
    salesRepEmployeeNumber: int | None = None
    creditLimit: Decimal | None = None


class CustomerCreate(CustomerBase):
    customerNumber: int | None = Field(default=None)


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customerName: str | None = None
    contactLastName: str | None = None
    contactFirstName: str | None = None
    phone: str | None = None
    addressLine1: str | None = None
    addressLine2: str | None = None
    city: str | None = None
    state: str | None = None
    postalCode: str | None = None
    country: str | None = None
    salesRepEmployeeNumber: int | None = None
    creditLimit: Decimal | None = None


class CustomerOut(CustomerBase):
    customerNumber: int


class CustomerDetailOut(CustomerOut):
    orders: list[OrderSummary] = Field(default_factory=list)
    payments: list[PaymentSummary] = Field(default_factory=list)


class OverallCounts(BaseModel):
    customers: int
    orders: int
    products: int
    employees: int
    offices: int
    payments: int
    orderdetails: int
    productlines: int