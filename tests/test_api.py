import pytest
from fastapi.testclient import TestClient

from vcheck.main import app


@pytest.fixture
def client():  # type: ignore[no-untyped-def]
    with TestClient(app) as test_client:
        yield test_client


def test_root_endpoint(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "model_available" in response.json()
    assert response.headers["X-Request-ID"]


def test_analyse_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/analyse",
        json={
            "text": (
                "URGENT parcel notice. Pay RM2 at http://parcel-payment.example "
                "or delivery will be cancelled."
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_level"] in {"Medium", "High"}
    assert payload["risk_score"] >= 20
    assert payload["warning_signs"]
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert "machine_learning" in payload
    assert payload["risk_score"] >= payload["rule_score"]


def test_supplied_request_id_is_preserved(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "demo-id"})
    assert response.headers["X-Request-ID"] == "demo-id"


def test_blank_like_message_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/analyse", json={"text": "!!!"})

    assert response.status_code == 422


def test_too_short_message_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/analyse", json={"text": "Hi"})
    assert response.status_code == 422


def test_rules_are_visible_for_auditability(client: TestClient) -> None:
    response = client.get("/api/v1/rules")

    assert response.status_code == 200
    rules = response.json()
    assert len(rules) >= 5
    assert all("explanation" in rule for rule in rules)


def test_model_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/model")
    assert response.status_code == 200
    assert "available" in response.json()
    assert "model_path" in response.json()


def test_model_reload_endpoint(client: TestClient) -> None:
    response = client.post("/api/v1/model/reload")
    assert response.status_code == 200
    assert "message" in response.json()
