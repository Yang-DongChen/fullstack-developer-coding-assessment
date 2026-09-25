from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


@dataclass
class SKU:
    id: str
    price: int
    available_quantity: int
    image: str
    options: dict[str, str]


PRODUCT = {
    "id": "pdp-001",
    "name": "Everyday Cotton Tee",
    "description": "A simple everyday T-shirt with multiple colour and size variants.",
    "options": [
        {"name": "colour", "values": ["Black", "White"]},
        {"name": "size", "values": ["S", "M", "L", "XL"]},
    ],
}

# 7 SKUs for 8 possible combinations: White + XL is intentionally unavailable.
SKUS: dict[str, SKU] = {
    "tee-black-s": SKU("tee-black-s", 2999, 10, "https://placehold.co/800x800?text=Black+S", {"colour": "Black", "size": "S"}),
    "tee-black-m": SKU("tee-black-m", 2999, 8, "https://placehold.co/800x800?text=Black+M", {"colour": "Black", "size": "M"}),
    "tee-black-l": SKU("tee-black-l", 3299, 0, "https://placehold.co/800x800?text=Black+L", {"colour": "Black", "size": "L"}),
    "tee-black-xl": SKU("tee-black-xl", 3299, 4, "https://placehold.co/800x800?text=Black+XL", {"colour": "Black", "size": "XL"}),
    "tee-white-s": SKU("tee-white-s", 2999, 5, "https://placehold.co/800x800?text=White+S", {"colour": "White", "size": "S"}),
    "tee-white-m": SKU("tee-white-m", 2999, 3, "https://placehold.co/800x800?text=White+M", {"colour": "White", "size": "M"}),
    "tee-white-l": SKU("tee-white-l", 3299, 2, "https://placehold.co/800x800?text=White+L", {"colour": "White", "size": "L"}),
}


class AddCartItem(BaseModel):
    sku_id: str = Field(min_length=1)
    quantity: int = Field(ge=1, le=99)


class CartItem(BaseModel):
    sku_id: str
    quantity: int
    unit_price: int
    options: dict[str, str]
    image: str


class Cart(BaseModel):
    items: list[CartItem]
    total_item_count: int
    total_price: int


class Store:
    """Small in-memory store suitable for the exercise.

    A single lock protects the inventory check + decrement + cart update +
    idempotency record as one critical section, so two workers cannot reserve
    the same final unit.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with getattr(self, "_lock", threading.Lock()):
            self.inventory = {sku_id: sku.available_quantity for sku_id, sku in SKUS.items()}
            self.cart: dict[str, CartItem] = {}
            self.idempotency: dict[str, tuple[str, dict[str, Any], int]] = {}

    def product_response(self) -> dict[str, Any]:
        return {
            **PRODUCT,
            "skus": [
                {
                    "id": sku.id,
                    "price": sku.price,
                    "available_quantity": self.inventory[sku.id],
                    "image": sku.image,
                    "options": sku.options,
                }
                for sku in SKUS.values()
            ],
        }

    def get_cart(self) -> Cart:
        items = list(self.cart.values())
        return Cart(
            items=items,
            total_item_count=sum(item.quantity for item in items),
            total_price=sum(item.quantity * item.unit_price for item in items),
        )

    def add_to_cart(self, payload: AddCartItem, key: str) -> tuple[dict[str, Any], int]:
        request_hash = hashlib.sha256(
            json.dumps(payload.model_dump(), sort_keys=True).encode("utf-8")
        ).hexdigest()

        with self._lock:
            # Same key + same payload returns the original result without changing stock/cart.
            existing = self.idempotency.get(key)
            if existing:
                old_hash, response_body, status = existing
                if old_hash != request_hash:
                    raise AppError(
                        409,
                        "IDEMPOTENCY_KEY_REUSED",
                        "The Idempotency-Key was already used with a different request.",
                    )
                return response_body, status

            sku = SKUS.get(payload.sku_id)
            if sku is None:
                raise AppError(404, "SKU_NOT_FOUND", "SKU does not exist.")

            current_stock = self.inventory[sku.id]
            if payload.quantity > current_stock:
                raise AppError(
                    409,
                    "INSUFFICIENT_STOCK",
                    f"Only {current_stock} unit(s) are currently available.",
                    {"available_quantity": current_stock},
                )

            self.inventory[sku.id] -= payload.quantity

            existing_item = self.cart.get(sku.id)
            if existing_item:
                existing_item.quantity += payload.quantity
            else:
                self.cart[sku.id] = CartItem(
                    sku_id=sku.id,
                    quantity=payload.quantity,
                    unit_price=sku.price,
                    options=sku.options,
                    image=sku.image,
                )

            cart = self.get_cart()
            response_body = {"message": "Item added to cart.", "cart": cart.model_dump()}
            self.idempotency[key] = (request_hash, response_body, 201)
            return response_body, 201


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def create_app() -> FastAPI:
    store = Store()
    app = FastAPI(title="Variant PDP API", version="1.0.0")
    app.state.store = store

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "Idempotency-Key"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": {"fields": [str(item.get("loc", [])) for item in exc.errors()]},
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        # Do not expose internal exception details to the client.
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Unexpected server error.", "details": {}}},
        )

    @app.get("/api/products/{product_id}")
    def get_product(product_id: str) -> dict[str, Any]:
        if product_id != PRODUCT["id"]:
            raise AppError(404, "PRODUCT_NOT_FOUND", "Product does not exist.")
        return store.product_response()

    @app.post("/api/cart/items", status_code=201)
    def add_cart_item(payload: AddCartItem, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> dict[str, Any]:
        if not idempotency_key or not idempotency_key.strip():
            raise AppError(400, "MISSING_IDEMPOTENCY_KEY", "Idempotency-Key header is required.")
        response, status = store.add_to_cart(payload, idempotency_key.strip())
        return JSONResponse(status_code=status, content=response)

    @app.get("/api/cart")
    def get_cart() -> dict[str, Any]:
        return store.get_cart().model_dump()

    return app


app = create_app()
