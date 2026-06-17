from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.database import get_db
from app.core.logger import logger


router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[schemas.CustomerOut])
def read_customers(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    logger.info("GET /customers called")
    return crud.get_customers(db, skip, limit)


@router.get("/{customer_id}", response_model=schemas.CustomerDetailOut)
def read_customer(customer_id: int, db: Session = Depends(get_db)):
    logger.info("GET /customers/%s called", customer_id)

    customer = crud.get_customer(db, customer_id)
    if customer is None:
        logger.warning("Customer not found: %s", customer_id)
        raise HTTPException(status_code=404, detail="Customer not found")

    customer_data = schemas.CustomerOut.model_validate(customer).model_dump()
    orders = [schemas.OrderSummary.model_validate(order) for order in crud.get_customer_orders(db, customer_id)]
    payments = [schemas.PaymentSummary.model_validate(payment) for payment in crud.get_customer_payments(db, customer_id)]

    return schemas.CustomerDetailOut(**customer_data, orders=orders, payments=payments)


@router.post("", response_model=schemas.CustomerOut, status_code=201)
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    logger.info("POST /customers called")
    return crud.create_customer(db, customer)


@router.put("/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(customer_id: int, customer: schemas.CustomerUpdate, db: Session = Depends(get_db)):
    logger.info("PUT /customers/%s called", customer_id)

    updated = crud.update_customer(db, customer_id, customer)
    if updated is None:
        logger.warning("Customer not found for update: %s", customer_id)
        raise HTTPException(status_code=404, detail="Customer not found")

    return updated


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    logger.info("DELETE /customers/%s called", customer_id)

    deleted = crud.delete_customer(db, customer_id)
    if deleted is None:
        logger.warning("Customer not found for deletion: %s", customer_id)
        raise HTTPException(status_code=404, detail="Customer not found")

    if deleted == "HAS_RELATIONS":
        raise HTTPException(status_code=400, detail="Cannot delete customer with related orders/payments")

    return {"message": "Customer deleted"}