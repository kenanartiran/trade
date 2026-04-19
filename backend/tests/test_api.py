import pyotp
from fastapi.testclient import TestClient

from app.main import app, state


client = TestClient(app)


def _auth_headers() -> dict[str, str]:
    login = client.post("/auth/login", json={"username": "trader", "password": "change-me"})
    assert login.status_code == 200
    challenge = login.json()["challenge_token"]

    code = pyotp.TOTP(state.user.totp_secret).now()
    verify = client.post("/auth/verify-2fa", json={"challenge_token": challenge, "code": code})
    assert verify.status_code == 200
    token = verify.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_requires_2fa_and_returns_access_token():
    headers = _auth_headers()
    response = client.get("/dashboard/summary", headers=headers)
    assert response.status_code == 200
    assert "account" in response.json()


def test_api_key_is_stored_encrypted_and_masked():
    headers = _auth_headers()
    plain_api_key = "demo-secret-api-key"

    save = client.post("/secrets/api-key", json={"broker": "ibkr", "api_key": plain_api_key}, headers=headers)
    assert save.status_code == 200

    assert state.encrypted_api_key is not None
    assert plain_api_key.encode("utf-8") not in state.encrypted_api_key

    read = client.get("/secrets/api-key", headers=headers)
    assert read.status_code == 200
    payload = read.json()
    assert payload["stored"] is True
    assert payload["masked"].endswith(plain_api_key[-4:])


def test_kill_switch_blocks_order_placement():
    headers = _auth_headers()
    enabled = client.post("/risk/kill-switch", json={"enabled": True}, headers=headers)
    assert enabled.status_code == 200

    blocked = client.post(
        "/broker/mock/orders",
        json={
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 1,
            "price": 100,
            "stop_loss": 95,
            "take_profit": 110,
        },
        headers=headers,
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Kill switch enabled"

    client.post("/risk/kill-switch", json={"enabled": False}, headers=headers)


def test_buy_order_updates_positions():
    headers = _auth_headers()
    before = client.get("/broker/mock/positions", headers=headers)
    assert before.status_code == 200

    order = client.post(
        "/broker/mock/orders",
        json={
            "symbol": "NVDA",
            "side": "buy",
            "quantity": 1,
            "price": 100,
            "stop_loss": 95,
            "take_profit": 120,
        },
        headers=headers,
    )
    assert order.status_code == 200

    after = client.get("/broker/mock/positions", headers=headers)
    assert after.status_code == 200
    symbols = {position["symbol"] for position in after.json()}
    assert "NVDA" in symbols
