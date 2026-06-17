from fastapi import FastAPI

from app.core.logger import logger
from app.routers import counts, customers


app = FastAPI(title="AI Fellowship Week 2 API", version="1.0.0")

app.include_router(customers.router)
app.include_router(counts.router)


@app.get("/")
def root():
    logger.info("GET / called")
    return {"message": "Week 2 API is running", "docs": "/docs"}