import asyncio
import time

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.database import SessionLocal, get_db
from app.core.logger import logger


router = APIRouter(tags=["counts"])


def _run_count(counter_function):
    with SessionLocal() as db:
        return counter_function(db)


async def _count_in_thread(counter_function):
    return await run_in_threadpool(_run_count, counter_function)


@router.get("/customers/count")
def customers_count(db: Session = Depends(get_db)):
    logger.info("GET /customers/count called")
    return {"customers": crud.get_customers_count(db)}


@router.get("/orders/count")
def orders_count(db: Session = Depends(get_db)):
    logger.info("GET /orders/count called")
    return {"orders": crud.get_orders_count(db)}


@router.get("/products/count")
def products_count(db: Session = Depends(get_db)):
    logger.info("GET /products/count called")
    return {"products": crud.get_products_count(db)}


@router.get("/employees/count")
def employees_count(db: Session = Depends(get_db)):
    logger.info("GET /employees/count called")
    return {"employees": crud.get_employees_count(db)}


@router.get("/offices/count")
def offices_count(db: Session = Depends(get_db)):
    logger.info("GET /offices/count called")
    return {"offices": crud.get_offices_count(db)}


@router.get("/payments/count")
def payments_count(db: Session = Depends(get_db)):
    logger.info("GET /payments/count called")
    return {"payments": crud.get_payments_count(db)}


@router.get("/orderdetails/count")
def orderdetails_count(db: Session = Depends(get_db)):
    logger.info("GET /orderdetails/count called")
    return {"orderdetails": crud.get_orderdetails_count(db)}


@router.get("/productlines/count")
def productlines_count(db: Session = Depends(get_db)):
    logger.info("GET /productlines/count called")
    return {"productlines": crud.get_productlines_count(db)}


@router.get("/overall_counts", response_model=schemas.OverallCounts)
async def overall_counts():
    logger.info("GET /overall_counts called")
    start_time = time.time()

    logger.info("Starting concurrent count queries")
    results = await asyncio.gather(
        _count_in_thread(crud.get_customers_count),
        _count_in_thread(crud.get_orders_count),
        _count_in_thread(crud.get_products_count),
        _count_in_thread(crud.get_employees_count),
        _count_in_thread(crud.get_offices_count),
        _count_in_thread(crud.get_payments_count),
        _count_in_thread(crud.get_orderdetails_count),
        _count_in_thread(crud.get_productlines_count),
    )
    logger.info("All concurrent queries completed")
    logger.info("/overall_counts completed in %.4f seconds", time.time() - start_time)

    return schemas.OverallCounts(
        customers=results[0],
        orders=results[1],
        products=results[2],
        employees=results[3],
        offices=results[4],
        payments=results[5],
        orderdetails=results[6],
        productlines=results[7],
    )