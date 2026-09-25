from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def setup_function() -> None:
    app.state.store.reset()


def test_product_returns_seeded_variants() -> None:
    response = client.get("/api/products/pdp-001")
    assert response.status_code == 200
    body = response.json()
    assert len(body["options"]) == 2
    assert len(body["skus"]) == 7
    assert any(sku["available_quantity"] == 0 for sku in body["skus"])
    assert response.status_code == 200


def test_add_to_cart_success() -> None:
    response = client.post(
        "/api/cart/items",
        headers={"Idempotency-Key": "test-success-1"},
        json={"sku_id": "tee-black-s", "quantity": 2},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["cart"]["total_item_count"] == 2
    assert body["cart"]["items"][0]["unit_price"] == 2999


def test_validation_errors() -> None:
    missing_key = client.post("/api/cart/items", json={"sku_id": "tee-black-s", "quantity": 1})
    assert missing_key.status_code == 400
    assert missing_key.json()["error"]["code"] == "MISSING_IDEMPOTENCY_KEY"

    bad_quantity = client.post(
        "/api/cart/items",
        headers={"Idempotency-Key": "test-validation-quantity"},
        json={"sku_id": "tee-black-s", "quantity": 0},
    )
    assert bad_quantity.status_code == 422
    assert bad_quantity.json()["error"]["code"] == "VALIDATION_ERROR"

    out_of_stock = client.post(
        "/api/cart/items",
        headers={"Idempotency-Key": "test-validation-stock"},
        json={"sku_id": "tee-black-l", "quantity": 1},
    )
    assert out_of_stock.status_code == 409
    assert out_of_stock.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    unknown_sku = client.post(
        "/api/cart/items",
        headers={"Idempotency-Key": "test-validation-sku"},
        json={"sku_id": "does-not-exist", "quantity": 1},
    )
    assert unknown_sku.status_code == 404
    assert unknown_sku.json()["error"]["code"] == "SKU_NOT_FOUND"


def test_idempotency_does_not_add_twice() -> None:
    headers = {"Idempotency-Key": "same-request"}
    payload = {"sku_id": "tee-white-s", "quantity": 2}

    first = client.post("/api/cart/items", headers=headers, json=payload)
    second = client.post("/api/cart/items", headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == first.json()

    cart = client.get("/api/cart").json()
    assert cart["total_item_count"] == 2


def test_same_idempotency_key_with_different_payload_is_rejected() -> None:
    headers = {"Idempotency-Key": "same-key-different-payload"}
    first = client.post(
        "/api/cart/items",
        headers=headers,
        json={"sku_id": "tee-black-s", "quantity": 1},
    )
    second = client.post(
        "/api/cart/items",
        headers=headers,
        json={"sku_id": "tee-white-s", "quantity": 1},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_stock_race_allows_only_available_units() -> None:
    # Reset the test SKU to one unit for an easy two-request race.
    app.state.store.inventory["tee-white-l"] = 1

    def reserve(key: str):
        return client.post(
            "/api/cart/items",
            headers={"Idempotency-Key": key},
            json={"sku_id": "tee-white-l", "quantity": 1},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reserve, ["race-1", "race-2"]))

    statuses = sorted(response.status_code for response in results)
    assert statuses == [201, 409]

    cart = client.get("/api/cart").json()
    assert cart["total_item_count"] == 1
    assert app.state.store.inventory["tee-white-l"] == 0
