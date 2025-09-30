# api/app.py
import os
import logging
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict
from uuid import uuid4
from datetime import datetime

# --- Logging setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orders-api")

# --- Feature flag from environment ---
ENABLE_GET_CREATE = True

app = FastAPI(title="Orders API", version="1.0")

# CORS (prototyp, v produkci omezit)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (MVP)
ORDERS: Dict[str, dict] = {}


# --- Models ---
class OrderCreate(BaseModel):
    customer_email: str = Field(..., examples=["user@example.com"])
    product_id: str = Field(..., examples=["sku_123"])
    quantity: int = Field(ge=1, default=1)


class OrderOut(BaseModel):
    id: str
    status: str
    created_at: str
    customer_email: str
    product_id: str
    quantity: int


# --- Middleware to log requests ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"➡️ {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"⬅️ {request.method} {request.url} → {response.status_code}")
    return response


# --- Health ---
@app.get("/", tags=["health"])
def health():
    logger.info("Health check called")
    return {"ok": True, "service": "orders-api", "version": "1.0"}


# --- POST (correct way) ---
@app.post("/orders", response_model=OrderOut, tags=["orders"])
def create_order(payload: OrderCreate):
    order_id = str(uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    doc = {
        "id": order_id,
        "status": "created",
        "created_at": now,
        "customer_email": payload.customer_email,
        "product_id": payload.product_id,
        "quantity": payload.quantity,
    }
    ORDERS[order_id] = doc
    logger.info(f"📝 [POST] Order created: {doc}")
    return doc


# --- GET read ---
@app.get("/orders/{order_id}", response_model=OrderOut, tags=["orders"])
def get_order(order_id: str):
    logger.info(f"🔍 Fetching order {order_id}")
    doc = ORDERS.get(order_id)
    if not doc:
        logger.warning(f"❌ Order {order_id} not found")
        raise HTTPException(status_code=404, detail="Order not found")
    logger.info(f"✅ Order found: {doc}")
    return doc


# --- OPTIONAL: GET-based create (enabled only by env var) ---
if ENABLE_GET_CREATE:

    @app.get("/orders/create", response_model=OrderOut, tags=["orders"])
    def create_order_get(
        customer_email: str = Query(..., description="Customer email"),
        product_id: str = Query(..., description="Product id / sku"),
        quantity: int = Query(1, ge=1, description="Quantity"),
    ):
        """
        HACK: Vytvoří objednávku přes GET (volitelně povoleno pomocí ENABLE_GET_CREATE=1).
        Tento endpoint je určený pouze pro rychlé testy / demo a není REST-konformní.
        """
        order_id = str(uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        doc = {
            "id": order_id,
            "status": "created",
            "created_at": now,
            "customer_email": customer_email,
            "product_id": product_id,
            "quantity": quantity,
        }
        ORDERS[order_id] = doc
        logger.info(f"📝 [GET] Order created: {doc}")
        return doc

else:
    logger.info("GET /orders/create is disabled (ENABLE_GET_CREATE != 1)")
