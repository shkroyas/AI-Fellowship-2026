from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.logger import logger


def get_customers(db: Session, skip: int = 0, limit: int = 10):
    logger.info("Fetching customers")
    return db.query(models.Customer).offset(skip).limit(limit).all()


def get_customer(db: Session, customer_id: int):
    logger.info("Fetching customer %s", customer_id)
    return db.query(models.Customer).filter(models.Customer.customerNumber == customer_id).first()


def get_customer_orders(db: Session, customer_id: int):
    logger.info("Fetching orders for customer %s", customer_id)
    return db.query(models.Order).filter(models.Order.customerNumber == customer_id).order_by(models.Order.orderNumber).all()


def get_customer_payments(db: Session, customer_id: int):
    logger.info("Fetching payments for customer %s", customer_id)
    return db.query(models.Payment).filter(models.Payment.customerNumber == customer_id).order_by(models.Payment.paymentDate).all()


def _next_customer_number(db: Session) -> int:
    highest_customer_number = db.query(func.max(models.Customer.customerNumber)).scalar()
    return 1 if highest_customer_number is None else highest_customer_number + 1


def create_customer(db: Session, customer: schemas.CustomerCreate):
    logger.info("Creating customer")

    customer_data = customer.model_dump(exclude_none=True)
    customer_data.setdefault("customerNumber", _next_customer_number(db))

    db_customer = models.Customer(**customer_data)
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


def update_customer(db: Session, customer_id: int, customer_data: schemas.CustomerUpdate):
    logger.info("Updating customer %s", customer_id)
    customer = get_customer(db, customer_id)

    if customer is None:
        return None

    for key, value in customer_data.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)

    db.commit()
    db.refresh(customer)
    return customer


def delete_customer(db: Session, customer_id: int):
    logger.info("Deleting customer %s", customer_id)
    customer = get_customer(db, customer_id)

    if customer is None:
        return None

    try:
        db.delete(customer)
        db.commit()
        return customer
    except IntegrityError:
        db.rollback()
        logger.warning("Customer %s has related records and cannot be deleted", customer_id)
        return "HAS_RELATIONS"


def _count_records(db: Session, column):
    return db.query(func.count(column)).scalar() or 0


def get_customers_count(db: Session):
    logger.info("Counting customers")
    return _count_records(db, models.Customer.customerNumber)


def get_orders_count(db: Session):
    logger.info("Counting orders")
    return _count_records(db, models.Order.orderNumber)


def get_products_count(db: Session):
    logger.info("Counting products")
    return _count_records(db, models.Product.productCode)


def get_employees_count(db: Session):
    logger.info("Counting employees")
    return _count_records(db, models.Employee.employeeNumber)


def get_offices_count(db: Session):
    logger.info("Counting offices")
    return _count_records(db, models.Office.officeCode)


def get_payments_count(db: Session):
    logger.info("Counting payments")
    return _count_records(db, models.Payment.customerNumber)


def get_orderdetails_count(db: Session):
    logger.info("Counting order details")
    return _count_records(db, models.OrderDetail.orderNumber)


def get_productlines_count(db: Session):
    logger.info("Counting product lines")
    return _count_records(db, models.ProductLine.productLine)